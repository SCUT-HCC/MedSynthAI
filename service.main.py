
"""
此文件为交互式问诊入口，已实现：
- 病例数据加载功能（支持相对路径、项目根相对路径及在项目内搜索）
- 移除批量处理相关逻辑，专注单病例/交互式会话
- 保留与原 MedicalWorkflow 的兼容（通过替换 virtual_patient.run 以接收人工输入）

用法示例：
  python service/main.py --dataset-path research/dataset/test_data.json --case-index 0
  python service/main.py --dataset-path /absolute/path/to/test_data.json
  python service/main.py --dataset-path research/dataset/test_data.json  # 在项目根下运行

注意：
- 请在项目根目录或通过 --dataset-path 指定数据文件路径运行此脚本。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from types import SimpleNamespace
from datetime import datetime
from typing import List, Dict, Any, Optional

# 项目根目录（service 目录的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 导入项目内模块
try:
    from research.workflow import MedicalWorkflow
    from guidance.loader import GuidanceLoader
    from config import LLM_CONFIG
except Exception as e:
    raise ImportError(f"无法导入项目模块，请确保在项目根目录运行。错误: {e}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="交互式终端问诊 (单病例模式)")
    parser.add_argument(
        '--dataset-path',
        type=str,
        default='research/dataset/test_data.json',
        help='病例数据 JSON 文件路径（数组形式），支持相对路径或绝对路径'
    )
    parser.add_argument(
        '--case-index',
        type=int,
        default=None,
        help='要交互的病例索引（从0开始）。如果不指定，会列出病例供选择'
    )
    parser.add_argument(
        '--max-steps',
        type=int,
        default=30,
        help='每个病例最大轮次'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default='results/interactive_logs',
        help='交互式会话日志保存目录（由 WorkflowLogger 管理）'
    )
    parser.add_argument(
        '--model-type',
        type=str,
        default='deepseek',
        help='用于 agents 的模型类型（不影响人工输入）'
    )
    parser.add_argument(
        '--department-filter',
        type=str,
        default=None,
        help='指定固定科室以加载对应的询问指导（可选）'
    )
    parser.add_argument(
        '--use_dynamic_guidance',
        action='store_true',
        default=True,
        help='是否启用动态科室指导（默认启用）'
    )
    parser.add_argument(
        '--use_inquiry_guidance',
        action='store_true',
        default=True,
        help='是否使用科室询问指导（默认启用）'
    )
    parser.add_argument(
        '--use_department_comparison',
        action='store_true',
        default=True,
        help='是否启用科室对比鉴别（默认启用）'
    )
    parser.add_argument(
        '--list-cases',
        action='store_true',
        help='仅列出数据集中病例概要并退出'
    )
    return parser.parse_args()


def load_dataset_with_fallback(dataset_path: str) -> List[Dict[str, Any]]:
    """
    加载数据集；如果路径不存在，尝试按下列顺序修正并查找：
      1. 将相对路径解释为项目根下的相对路径
      2. 在项目下搜索同名文件（test_data.json）
    返回 JSON 数组（list），若无效则抛出异常。
    """
    # 直接存在则使用
    if os.path.exists(dataset_path):
        path_used = dataset_path
    else:
        # 尝试作为项目根的相对路径
        alt = os.path.join(PROJECT_ROOT, dataset_path)
        if os.path.exists(alt):
            path_used = alt
            print(f"已将数据集路径解释为项目根相对路径: {path_used}")
        else:
            # 在项目内搜索同名文件（只匹配文件名）
            target_name = os.path.basename(dataset_path)
            found = None
            for root, _, files in os.walk(PROJECT_ROOT):
                if target_name in files:
                    found = os.path.join(root, target_name)
                    break
            if found:
                path_used = found
                print(f"在项目中找到数据集并使用: {path_used}")
            else:
                raise FileNotFoundError(
                    f"数据集文件未找到: {dataset_path}\n"
                    f"已尝试项目根 {PROJECT_ROOT}，请检查路径或使用 --dataset-path 指定绝对路径。"
                )

    # 读取并验证 JSON
    try:
        with open(path_used, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"数据集 JSON 格式错误: {e}")
    except Exception as e:
        raise Exception(f"读取数据集失败: {e}")

    if not isinstance(data, list):
        raise ValueError("数据集应为 JSON 数组（list），每个元素为一个病例 dict。")

    print(f"已加载数据集: {path_used} （共 {len(data)} 个病例）")
    return data


def interactive_patient_run_factory():
    """
    返回一个 callable 用以替换 VirtualPatientAgent.run。
    Signature: (worker_inquiry: str, is_first_epoch: bool, patient_case: dict) -> object-with-current_chat
    支持简单命令：
      :exit / :quit / :q  -> 退出当前交互
      :show_history       -> 返回特殊标记，调用方可根据需要显示历史
      :show_triage        -> 返回特殊标记，调用方可显示分诊信息
    """
    def interactive_run(worker_inquiry: str = "", is_first_epoch: bool = False, patient_case: dict = None):
        print("\n" + "=" * 60)
        role = "首轮医生" if is_first_epoch else "医生"
        print(f"[{role}] 提问: {worker_inquiry}")
        print("请输入患者的回答（支持命令 :exit/:quit/:q(退出交互式会话), :show_history(打印当前完整对话历史), :show_triage（打印当前分诊信息）：")
        try:
            resp = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            raise KeyboardInterrupt("用户中断输入")

        if not resp:
            resp = "患者未提供描述"

        if resp.lower() in (":exit", ":quit", ":q"):
            # 抛出中断以便外层优雅处理
            raise KeyboardInterrupt("用户请求退出交互式会话")
        if resp == ":show_history":
            return SimpleNamespace(current_chat=":show_history")
        if resp == ":show_triage":
            return SimpleNamespace(current_chat=":show_triage")

        return SimpleNamespace(current_chat=resp)

    return interactive_run


def run_interactive_case(case_data: Dict[str, Any], args: argparse.Namespace, case_index: int = 0):
    # GuidanceLoader 初始化
    loader = GuidanceLoader(
        department_guidance="",
        use_dynamic_guidance=args.use_dynamic_guidance,
        use_department_comparison=args.use_department_comparison,
        department_guidance_file="guidance.department_inquiry_guidance.json",
        comparison_rules_file="guidance.department_comparison_guidance.json"
    )

    department_guidance = ""
    if args.use_inquiry_guidance and args.department_filter:
        dept_guidance = loader.load_inquiry_guidance(args.department_filter)
        if dept_guidance:
            department_guidance = dept_guidance
            print(f"已加载固定科室询问指导: {args.department_filter}")
        else:
            print(f"未能加载固定科室询问指导: {args.department_filter}，将使用默认/动态指导")

    # 创建 MedicalWorkflow 实例（与批处理版本保持接口兼容）
    workflow = MedicalWorkflow(
        case_data=case_data,
        model_type=args.model_type,
        llm_config=LLM_CONFIG.copy(),
        max_steps=args.max_steps,
        log_dir=args.log_dir,
        case_index=case_index,
        controller_mode="normal",
        guidance_loader=loader,
        department_guidance=department_guidance
    )

    # 用交互函数替换虚拟患者 run 方法
    interactive_runner = interactive_patient_run_factory()
    try:
        workflow.step_executor.virtual_patient.run = interactive_runner
    except Exception as e:
        raise RuntimeError(f"无法替换 virtual_patient.run：{e}")

    # 交互说明与启动
    print("\n" + "#" * 60)
    print(f"即将交互的病例索引: {case_index}，主诉: {case_data.get('病案介绍', {}).get('主诉', '未知')}")
    print("交互说明：在提示时输入患者回答；输入 :exit 或 :quit 以退出；输入 :show_history/:show_triage 查看信息。")
    print("#" * 60 + "\n")

    try:
        log_path = workflow.run()
        print(f"\n工作流执行完成，日志路径: {log_path}")
    except KeyboardInterrupt as e:
        # 优雅终止：展示当前状态摘要并返回
        print("\n用户中断交互会话，正在保存并显示当前进度...")
        try:
            status = workflow.get_current_status()
            summary = workflow.get_medical_summary()
            print("\n当前工作流状态:")
            print(json.dumps(status, ensure_ascii=False, indent=2))
            print("\n当前医疗摘要:")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            print(f"日志文件（可能为部分内容）: {workflow.logger.get_log_file_path()}")
        except Exception:
            pass
        return

    # 会话结束后打印对话与分诊摘要
    print("\n=== 最终对话历史 ===")
    try:
        print(workflow.get_conversation_history() or "无对话历史")
    except Exception:
        print("无法获取对话历史")

    print("\n=== 最终分诊与摘要 ===")
    try:
        print(json.dumps(workflow.get_medical_summary(), ensure_ascii=False, indent=2))
    except Exception:
        print("无法获取分诊/摘要信息")

    print("\n交互式会话结束。")


def main():
    args = parse_arguments()

    # 创建日志目录
    os.makedirs(args.log_dir, exist_ok=True)

    # 加载数据集（包含路径回退及查找）
    try:
        dataset = load_dataset_with_fallback(args.dataset_path)
    except Exception as e:
        print(f"错误：{e}")
        return 1

    total = len(dataset)
    if total == 0:
        print("数据集中没有病例。请检查数据文件内容。")
        return 1

    # 列出病例概要并退出（辅助功能）
    if args.list_cases:
        print(f"数据集中共 {total} 个病例，概要（前50字符）：\n")
        for idx, case in enumerate(dataset):
            brief = str(case.get("病案介绍", {}).get("主诉", ""))[:50]
            print(f"[{idx}] 主诉: {brief}")
        return 0

    # 选择病例索引：如果未指定，展示简短列表供选择
    selected_index = args.case_index
    if selected_index is None:
        print(f"数据集中共 {total} 个病例，请输入要交互的病例索引（0 - {total-1}）：")
        while True:
            try:
                s = input("> ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n用户中断，退出。")
                return 1
            if not s:
                print("请输入索引或 Ctrl-C 退出。")
                continue
            try:
                si = int(s)
                if 0 <= si < total:
                    selected_index = si
                    break
                else:
                    print(f"索引越界，请输入 0 - {total-1}。")
            except ValueError:
                print("请输入合法的整数索引。")

    if not (0 <= selected_index < total):
        print(f"错误：病例索引越界 (0..{total-1})，当前: {selected_index}")
        return 1

    # 运行交互式会话（单个病例）
    case_data = dataset[selected_index]
    run_interactive_case(case_data, args, case_index=selected_index)

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code if isinstance(exit_code, int) else 0)
    except Exception as exc:
        print(f"交互式主程序出现异常: {exc}")
        sys.exit(1)