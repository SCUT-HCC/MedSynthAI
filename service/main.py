"""
AIM医疗问诊工作流批处理系统
使用多线程并行处理数据集中的所有病例样本
"""

import argparse
import json
import logging
import os
import sys
import time
import threading
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any, List, Optional

# 导入本地模块
from workflow.medical_workflow import MedicalWorkflow
from guidance.loader import GuidanceLoader
from service.workflow.step_executor import StepExecutor

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from config import LLM_CONFIG

from guidance.loader import GuidanceLoader

def setup_logging(log_dir: str, log_level: str = "INFO") -> None:
    """设置日志记录配置"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 设置日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"batch_processing_{timestamp}.log")

    # 移除所有现有的处理器，以避免重复记录
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    # 配置日志记录
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    

def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--department_guidance_file', 
        type=str, 
        default='guidance/department_inquiry_guidance.json', 
        help='动态询问指导加载路径'
    )
    parser.add_argument(
        '--comparison_rules_file', 
        type=str, 
        default='guidance/department_comparison_guidance.json', 
        help='加载科室对比指导路径'
    )
    # 数据和输出配置
    parser.add_argument(
        '--log-dir', 
        type=str, 
        default='results/results09010-score_driven',
        help='日志文件保存目录'
    )
    parser.add_argument(
        '--max-steps', 
        type=int, 
        default=30,
        help='每个工作流的最大执行步数'
    )
    parser.add_argument(
        '--department_filter', 
        type=str, 
        default=None,
        help='筛选特定一级科室的病例 (例如: 内科, 外科, 儿科等)'
    )
    parser.add_argument(
        '--use_inquiry_guidance', 
        action='store_true', 
        default=True,
        help='是否使用科室特定的询问指导 (无论是固定指导还是询问指导，默认: True)'
    )
    parser.add_argument(
        '--use_dynamic_guidance', 
        action='store_true', 
        default=True,
        help='是否使用动态询问科室指导 (默认: True)'
    )
    parser.add_argument(
        '--use_department_comparison', 
        action='store_true', 
        default=True,
        help='是否使用科室对比鉴别功能 (默认: True)'
    )

    # 模型配置
    available_models = list(LLM_CONFIG.keys())
    parser.add_argument(
        '--model-type', 
        type=str, 
        choices=available_models,
        default='deepseek',
        help=f'使用的语言模型类型，可选: {", ".join(available_models)}'
    )
    parser.add_argument(
        '--list-models', 
        action='store_true',
        help='显示所有可用的模型配置并退出'
    )
    parser.add_argument(
        '--model-config', 
        type=str, 
        default=None,
        help='模型配置JSON字符串（可选，覆盖默认配置）'
    )
    parser.add_argument(
        '--controller-mode',
        type=str,
        choices=['normal', 'sequence', 'score_driven'],
        default='normal',
        help='任务控制器模式：normal为智能模式（需要LLM推理），sequence为顺序模式（直接选择第一个任务），score_driven为分数驱动模式（选择当前任务组中分数最低的任务）'
    )
    
    
    # 调试和日志
    parser.add_argument(
        '--log-level', 
        type=str, 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志记录级别'
    )
    parser.add_argument(
        '--progress-interval', 
        type=int, 
        default=10,
        help='进度报告间隔（秒）'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='试运行模式，只验证配置不执行处理'
    )
    
    return parser.parse_args()

def prepare_for_interactive(args: argparse.Namespace):
    # GuidanceLoader 初始化
    loader = GuidanceLoader(
        department_guidance="",
        use_dynamic_guidance=args.use_dynamic_guidance,
        use_department_comparison=args.use_department_comparison,
        department_guidance_file=args.department_guidance_file,
        comparison_rules_file=args.comparison_rules_file,
    )

    department_guidance = ""
    if args.use_inquiry_guidance and args.department_filter:
        department_guidance = loader.load_inquiry_guidance(args.department_filter)

    # 创建 MedicalWorkflow 实例
    workflow = MedicalWorkflow(
        model_type=args.model_type,
        llm_config=LLM_CONFIG.copy(),
        max_steps=args.max_steps,
        log_dir=args.log_dir,
        controller_mode="normal",
        guidance_loader=loader,
        department_guidance=department_guidance
    )
    return workflow

def interactive(worker_inquiry: str, is_first_epoch: bool) -> str:
    """仅获取患者回答并返回"""
    print("\n" + "=" * 60)
    role = "首轮医生" if is_first_epoch else "医生"
    print(f"[{role}] 提问: {worker_inquiry}")
    print("请输入患者的回答（输入 :exit/:quit/:q 以退出）：")
    
    try:
        resp = input("> ").strip()
        if not resp:
            print("\n[警告] 未提供回答")
            print("在提示中输入患者回答。输入 :exit / :quit / :q 可退出会话。")
            try:
                resp = input("患者（终端输入）: ").strip()
            except (KeyboardInterrupt, EOFError):
                raise KeyboardInterrupt("用户中断输入")
            if not resp:
                resp = "患者未提供描述"
                
        if resp.lower() in (":exit", ":quit", ":q"):
            raise KeyboardInterrupt("用户请求退出交互式会话")
            
        return resp
    except KeyboardInterrupt as e:
        # 传递中断信号
        raise e
def process_interaction(workflow: MedicalWorkflow, args: argparse.Namespace, patient_response: str):
    """处理交互流程的其余步骤"""
    # 获取工作流内部组件
    task_manager = workflow.task_manager
    logger = workflow.logger
    conversation_history = workflow.conversation_history
    current_hpi = workflow.current_hpi
    current_ph = workflow.current_ph
    current_chief_complaint = workflow.current_chief_complaint
    current_triage = workflow.current_triage
    step_executor = workflow.step_executor
    resp = patient_response  # 初始患者回答
    
    try:
        # 执行问诊步骤
        for step in range(1, args.max_steps + 1):
            if task_manager.is_workflow_completed():
                print(f"所有任务已完成，工作流在第 {step} 步结束")
                break

            task_manager.update_step(step)
            current_phase = task_manager.get_current_phase()
            pending_tasks = task_manager.get_pending_tasks(current_phase)
            logger.log_step_start(step, current_phase.value, pending_tasks)

            # 执行单步
            step_result = step_executor.execute_step(
                step_num=step,
                task_manager=task_manager,
                logger=logger,
                conversation_history=conversation_history,
                previous_hpi=current_hpi,
                previous_ph=current_ph,
                previous_chief_complaint=current_chief_complaint,
                previous_department=f"{current_triage.get('primary_department','')}-{current_triage.get('secondary_department','')}",
                previous_candidate_department=f"{current_triage.get('candidate_primary_department','')}-{current_triage.get('candidate_secondary_department','')}",
                previous_triage_reasoning=current_triage.get("triage_reasoning", ""),
                current_guidance=workflow.current_guidance if hasattr(workflow, 'current_guidance') else "",
                patient_response=resp,
                is_first_step=(step == 1),
                doctor_question=getattr(workflow, "_last_doctor_question", "")
            )

            if not step_result.get("success", False):
                print(f"Step {step} 执行失败: {step_result.get('errors')}")
                break

            # 更新本地工作流状态
            workflow._update_workflow_state(step_result)
            conversation_history = step_result.get("conversation_history", conversation_history)
            current_hpi = step_result.get("updated_hpi", current_hpi)
            current_ph = step_result.get("updated_ph", current_ph)
            current_chief_complaint = step_result.get("updated_chief_complaint", current_chief_complaint)
            current_triage = step_result.get("triage_result", current_triage)


            # 记录 step_complete 日志
            logger.log_step_complete(
                step_num=step,
                doctor_question=step_result.get("doctor_question", ""),
                conversation_history=conversation_history,
                task_completion_summary=step_result.get("task_completion_summary", {})
            )

            # 终端即时输出本轮信息
            print("\n--- 本轮终端输出 ---")
            print(f"当前轮次: {step}")
            print(f"任务管理器当前步骤: {current_phase.value}")
            print(f"{current_hpi or '（无）'}")
            print(f"{current_ph or '（无）'}")
            print(f"当前主诉: {current_chief_complaint or '（无）'}")
            print(f"当前分诊结果: {current_triage or '（无）'}")
            completion_summary = task_manager.get_completion_summary()
            print("阶段完成进度:")
            for phase_name, phase_info in completion_summary["phases"].items():
                status = "✓" if phase_info["is_completed"] else "○"
                print(f"  {status} {phase_name}: {phase_info['completed']}/{phase_info['total']} ({phase_info['completion_rate']:.1%})")
            print("当前对话历史（预览）:")
            print(conversation_history or "（无）")
            tr = step_result.get("triage_result", {})
            if tr:
                print("分诊结果:")
                print(f"  推荐科室: {tr.get('primary_department','')} - {tr.get('secondary_department','')}")
                print(f"  候选科室: {tr.get('candidate_primary_department','')} - {tr.get('candidate_secondary_department','')}")
            print("----------------------\n")

            # 获取下一轮患者输入（调用interactive获取回答）
            worker_inquiry = step_result.get("doctor_question", "请问还有什么需要补充的吗？")
            try:
                resp = interactive(worker_inquiry, is_first_epoch=False)
            except KeyboardInterrupt:
                raise KeyboardInterrupt("用户中断输入")


        # 循环结束后记录完成
        final_summary = task_manager.get_completion_summary()
        logger.log_workflow_complete(total_steps=step if 'step' in locals() else 0, final_summary=final_summary, success=task_manager.is_workflow_completed())

    except KeyboardInterrupt:
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
        print(conversation_history or "无对话历史")
    except Exception:
        print("无法获取对话历史")

    print("\n=== 最终分诊与摘要 ===")
    try:
        print(json.dumps(workflow.get_medical_summary(), ensure_ascii=False, indent=2))
    except Exception:
        print("无法获取分诊/摘要信息")

    print("\n交互式会话结束。")


def main():
    """主入口函数"""
    # 解析参数
    args = parse_arguments()
    
    # 设置日志
    setup_logging(args.log_dir, args.log_level)
    
    logging.info("=" * 60)
    logging.info("终端交互式问诊系统启动")
    logging.info("=" * 60)
    
    # 验证参数
    if args.max_steps <= 0:
            raise ValueError("最大步数必须大于0")
        
    # 验证模型类型
    if args.model_type not in LLM_CONFIG:
            available_models = ', '.join(LLM_CONFIG.keys())
            raise ValueError(f"不支持的模型类型: {args.model_type}，可用模型: {available_models}")
        
    logging.info(f"使用模型: {args.model_type} ({LLM_CONFIG[args.model_type]['class']})")
        

    # 运行交互
    workflow = prepare_for_interactive(args)
    try:
        # 获取首轮患者回答
        initial_response = interactive("您好，请问您哪里不舒服？", is_first_epoch=True)
        # 处理后续流程
        process_interaction(workflow, args, initial_response)
    except KeyboardInterrupt:
        print("\n会话已退出")
    
    return 0



    

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)