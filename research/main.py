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
from workflow import MedicalWorkflow
from config import LLM_CONFIG

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from guidance.loader import GuidanceLoader

class BatchProcessor:
    """批处理管理器，负责协调多线程执行和状态管理"""
    
    def __init__(self, num_threads: int = 20):
        self.num_threads = num_threads
        self.lock = threading.Lock()  # 线程安全锁
        self.processed_count = 0  # 已处理样本数
        self.success_count = 0    # 成功处理数
        self.failed_count = 0     # 失败处理数
        self.skipped_count = 0    # 跳过的样本数
        self.results = []         # 结果列表
        self.failed_samples = []  # 失败样本列表
        self.start_time = None    # 开始时间
        
    def update_progress(self, success: bool, result: Dict[str, Any] = None, 
                       error: Exception = None, sample_index: int = None):
        """线程安全地更新处理进度"""
        with self.lock:
            self.processed_count += 1
            if success:
                self.success_count += 1
                if result:
                    self.results.append(result)
            else:
                self.failed_count += 1
                if error and sample_index is not None:
                    self.failed_samples.append({
                        'sample_index': sample_index,
                        'error': str(error),
                        'timestamp': datetime.now().isoformat()
                    })
    
    def update_skipped(self, sample_index: int):
        """线程安全地更新跳过样本计数"""
        with self.lock:
            self.skipped_count += 1
            logging.info(f"样本 {sample_index} 已完成，跳过处理")
                    
    def get_progress_stats(self) -> Dict[str, Any]:
        """获取当前进度统计"""
        with self.lock:
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            return {
                'processed': self.processed_count,
                'success': self.success_count,
                'failed': self.failed_count,
                'skipped': self.skipped_count,
                'success_rate': self.success_count / max(self.processed_count, 1),
                'elapsed_time': elapsed_time,
                'samples_per_minute': self.processed_count / max(elapsed_time / 60, 0.01)
            }

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
        description="AIM医疗问诊工作流批处理系统",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # 数据输入配置
    parser.add_argument(
        '--dataset-path', 
        type=str, 
        default='research/dataset/test_data.json',
        help='数据集JSON文件路径'
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
        '--output-dir', 
        type=str, 
        default='results/batch_results',
        help='批处理结果保存目录'
    )
    parser.add_argument(
        '--batch-log-dir', 
        type=str, 
        default='results/logs',
        help='批处理运行时日志保存目录'
    )
    # 执行参数
    parser.add_argument(
        '--num-threads', 
        type=int, 
        default=1,
        help='并行处理线程数'
    )
    parser.add_argument(
        '--max-steps', 
        type=int, 
        default=30,
        help='每个工作流的最大执行步数'
    )
    parser.add_argument(
        '--start-index', 
        type=int, 
        default=0,
        help='开始处理的样本索引'
    )
    parser.add_argument(
        '--end-index', 
        type=int, 
        default=5000,
        help='结束处理的样本索引（不包含）'
    )
    parser.add_argument(
        '--sample-limit', 
        type=int, 
        default=None,
        help='限制处理的样本数量（用于测试）'
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
        default='score_driven',
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

def is_case_completed(log_dir: str, case_index: int) -> bool:
    """
    检查指定case是否已经完成工作流
    如果存在不完整的文件则删除，确保每个case在目录中只出现一次
    
    Args:
        log_dir: 日志目录
        case_index: case序号
        
    Returns:
        bool: 如果case已完成返回True，否则返回False
    """
    # 构建文件路径模式：workflow_*_case_{case_index:04d}.jsonl
    pattern = os.path.join(log_dir, f"workflow_*_case_{case_index:04d}.jsonl")
    matching_files = glob.glob(pattern)
    
    if not matching_files:
        return False
    
    # 应该只有一个匹配的文件
    if len(matching_files) > 1:
        logging.warning(f"发现多个匹配文件 case {case_index}: {matching_files}")
    
    # 检查每个匹配的文件
    for log_file in matching_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # 读取最后一行
                lines = f.readlines()
                if not lines:
                    # 文件为空，删除
                    try:
                        os.remove(log_file)
                        logging.info(f"删除空文件: {log_file}")
                    except (OSError, FileNotFoundError, PermissionError) as e:
                        # 文件删除失败不影响主流程，记录警告即可
                        logging.warning(f"无法删除空文件 {log_file}: {e}")
                    continue
                
                last_line = lines[-1].strip()
                if not last_line:
                    # 最后一行为空，删除
                    try:
                        os.remove(log_file)
                        logging.info(f"删除最后一行为空的文件: {log_file}")
                    except (OSError, FileNotFoundError, PermissionError) as e:
                        # 文件删除失败不影响主流程，记录警告即可
                        logging.warning(f"无法删除最后一行为空的文件 {log_file}: {e}")
                    continue
                
                # 解析最后一行的JSON
                try:
                    last_entry = json.loads(last_line)
                    if last_entry.get("event_type") == "workflow_complete":
                        # 找到完整的文件
                        logging.info(f"发现已完成的case {case_index}: {log_file}")
                        return True
                    else:
                        # 文件不完整，删除
                        try:
                            os.remove(log_file)
                            logging.info(f"删除不完整的文件: {log_file}")
                        except (OSError, FileNotFoundError, PermissionError) as e:
                            # 文件删除失败不影响主流程，记录警告即可
                            logging.warning(f"无法删除不完整的文件 {log_file}: {e}")
                        continue
                        
                except json.JSONDecodeError:
                    # JSON解析失败，删除文件
                    try:
                        os.remove(log_file)
                        logging.info(f"删除JSON格式错误的文件: {log_file}")
                    except (OSError, FileNotFoundError, PermissionError) as e:
                        # 文件删除失败不影响主流程，记录警告即可
                        logging.warning(f"无法删除JSON格式错误的文件 {log_file}: {e}")
                    continue
                    
        except Exception as e:
            logging.warning(f"检查文件 {log_file} 时出错: {e}")
            # 出现异常也删除文件，避免后续问题
            try:
                os.remove(log_file)
                logging.info(f"删除异常文件: {log_file}")
            except (OSError, FileNotFoundError, PermissionError) as delete_error:
                # 修复1：明确指定要捕获的异常类型
                # 修复2：添加解释性注释
                # 文件删除失败不是致命错误，可能是权限问题或文件已被其他进程占用
                # 记录警告后继续处理，不中断整个检查流程
                logging.warning(f"无法删除异常文件 {log_file}: {delete_error}")
            except Exception as unexpected_error:
                # 处理其他意外的删除异常（比如磁盘满等）
                # 这些错误也不应该中断检查流程
                logging.error(f"删除文件时发生意外错误 {log_file}: {unexpected_error}")
            continue
    
    # 所有匹配的文件都被删除或没有完整的文件
    return False

def load_dataset(dataset_path: str, start_index: int = 0, 
                end_index: Optional[int] = None, 
                sample_limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """加载和验证数据集"""
    logging.info(f"正在加载数据集: {dataset_path}")
    
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"数据集文件不存在: {dataset_path}")
    
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            full_dataset = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"数据集JSON格式错误: {e}")
    except Exception as e:
        raise Exception(f"加载数据集失败: {e}")
    
    if not isinstance(full_dataset, list):
        raise ValueError("数据集应该是包含病例的JSON数组")
    
    total_samples = len(full_dataset)
    logging.info(f"数据集总样本数: {total_samples}")
    
    # 确定处理范围
    if end_index is None:
        end_index = total_samples
    
    end_index = min(end_index, total_samples)
    start_index = max(0, start_index)
    
    if sample_limit:
        end_index = min(start_index + sample_limit, end_index)
    
    if start_index >= end_index:
        raise ValueError(f"无效的索引范围: start_index={start_index}, end_index={end_index}")
    
    # 提取指定范围的数据
    dataset = full_dataset[start_index:end_index]
    
    logging.info(f"将处理样本范围: [{start_index}, {end_index}), 共 {len(dataset)} 个样本")
    
    # 验证数据格式
    for i, sample in enumerate(dataset[:5]):  # 只验证前5个样本
        if not isinstance(sample, dict):
            raise ValueError(f"样本 {start_index + i} 格式错误，应为字典类型")
        
        required_keys = ['病案介绍']
        for key in required_keys:
            if key not in sample:
                logging.warning(f"样本 {start_index + i} 缺少必需字段: {key}")
    
    return dataset


def process_single_sample(sample_data: Dict[str, Any], sample_index: int, 
                         args: argparse.Namespace, 
                         processor: BatchProcessor) -> Dict[str, Any]:
    """处理单个样本的工作函数"""
    thread_id = threading.current_thread().ident
    start_time = time.time()
    
    
    try:
        # 使用 LLM_CONFIG 作为基础配置
        # BaseAgent 会根据 model_type 自动选择正确的模型配置
        llm_config = LLM_CONFIG.copy()
        
        # 如果用户提供了额外的模型配置，则合并到对应的模型配置中
        if args.model_config:
            try:
                user_config = json.loads(args.model_config)
                # 更新选定模型的配置
                if args.model_type in llm_config:
                    llm_config[args.model_type]["params"].update(user_config.get("params", {}))
                else:
                    logging.warning(f"样本 {sample_index}: 模型类型 {args.model_type} 不存在，忽略用户配置")
            except json.JSONDecodeError:
                logging.warning(f"样本 {sample_index}: 模型配置JSON格式错误，使用默认配置")
        
        #是否使用固定科室模式
        department_guidance = ""

        # 初始化 GuidanceLoader
        loader = GuidanceLoader(
            department_guidance = department_guidance,
            use_dynamic_guidance=args.use_dynamic_guidance,
            use_department_comparison=args.use_department_comparison,
            department_guidance_file=args.department_guidance_file,
            comparison_rules_file=args.comparison_rules_file
        )

        if args.use_inquiry_guidance:
            if args.department_filter:
                # 固定科室模式
                department_guidance = loader.load_inquiry_guidance(args.department_filter)
                
                # 将加载好的指导同步回 loader 实例
                loader.department_guidance = department_guidance

                if department_guidance:
                    print(f"✅ 已加载 '{args.department_filter}' 科室的固定询问指导")
                else:
                    print(f"⚠️ 未能加载 '{args.department_filter}' 科室的询问指导，将使用默认询问模式")
            else:
                # 动态指导模式
                if args.max_steps > 1 and args.use_dynamic_guidance:
                    print(f"🔄 已启用动态科室询问指导模式")
                else:
                    print(f"⚠️ 单步问诊不需要动态指导，将使用默认模式")

        # 创建工作流实例
        workflow = MedicalWorkflow(
            case_data=sample_data,
            model_type=args.model_type,
            llm_config=llm_config,
            max_steps=args.max_steps,
            log_dir=args.log_dir,
            case_index=sample_index,
            controller_mode=args.controller_mode,
            guidance_loader=loader, #将 loader 传递给 MedicalWorkflow
            department_guidance=department_guidance
        )
        
        # 执行工作流
        logging.debug(f"线程 {thread_id}: 开始处理样本 {sample_index}")
        log_file_path = workflow.run()
        
        execution_time = time.time() - start_time
        
        # 获取执行结果
        workflow_status = workflow.get_current_status()
        medical_summary = workflow.get_medical_summary()
        
        # 构建结果
        result = {
            'sample_index': sample_index,
            'thread_id': thread_id,
            'execution_time': execution_time,
            'log_file_path': log_file_path,
            'workflow_status': workflow_status,
            'medical_summary': medical_summary,
            'processed_at': datetime.now().isoformat()
        }
        
        
        # 更新进度
        processor.update_progress(success=True, result=result)
        
        logging.info(f"样本 {sample_index} 处理完成 (耗时: {execution_time:.2f}s, "
                    f"步数: {workflow_status['current_step']}, "
                    f"成功: {workflow_status['workflow_success']})")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"样本 {sample_index} 处理失败: {str(e)}"
        
        
        logging.error(error_msg)
        processor.update_progress(success=False, error=e, sample_index=sample_index)
        
        # 返回错误结果
        return {
            'sample_index': sample_index,
            'thread_id': thread_id,
            'execution_time': execution_time,
            'error': str(e),
            'processed_at': datetime.now().isoformat(),
            'success': False
        }

def print_progress_report(processor: BatchProcessor, total_samples: int):
    """打印进度报告"""
    stats = processor.get_progress_stats()
    
    print(f"\n=== 处理进度报告 ===")
    print(f"已处理: {stats['processed']}/{total_samples} ({stats['processed']/total_samples:.1%})")
    print(f"成功: {stats['success']} | 失败: {stats['failed']} | 跳过: {stats['skipped']} | 成功率: {stats['success_rate']:.1%}")
    print(f"耗时: {stats['elapsed_time']:.1f}s | 处理速度: {stats['samples_per_minute']:.1f} 样本/分钟")
    remaining_samples = total_samples - stats['processed'] - stats['skipped']
    print(f"预计剩余时间: {remaining_samples / max(stats['samples_per_minute'] / 60, 0.01):.1f}s")
    print("=" * 50)

def run_workflow_batch(dataset: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    """执行批量工作流处理"""
    total_samples = len(dataset)
    logging.info(f"开始批量处理 {total_samples} 个样本，使用 {args.num_threads} 个线程")
    
    # 创建批处理管理器
    processor = BatchProcessor(num_threads=args.num_threads)
    processor.start_time = time.time()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    
    # 启动进度监控线程
    def progress_monitor():
        while processor.processed_count + processor.skipped_count < total_samples:
            time.sleep(args.progress_interval)
            if processor.processed_count + processor.skipped_count < total_samples:
                print_progress_report(processor, total_samples)
    
    progress_thread = threading.Thread(target=progress_monitor, daemon=True)
    progress_thread.start()
    
    try:
        # 使用线程池执行批处理
        with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
            # 提交所有任务
            future_to_index = {}
            for i, sample_data in enumerate(dataset):
                sample_index = args.start_index + i
                
                # 检查case是否已经完成
                if is_case_completed(args.log_dir, sample_index):
                    processor.update_skipped(sample_index)
                    continue
                
                future = executor.submit(
                    process_single_sample, 
                    sample_data, 
                    sample_index, 
                    args, 
                    processor
                )
                future_to_index[future] = sample_index
            
            # 等待所有任务完成
            for future in as_completed(future_to_index):
                sample_index = future_to_index[future]
                try:
                    _ = future.result()  # 结果已经在process_single_sample中处理
                except Exception as e:
                    logging.error(f"线程执行异常 (样本 {sample_index}): {e}")
    
    except KeyboardInterrupt:
        logging.warning("收到中断信号，正在停止处理...")
        executor.shutdown(wait=False)
        raise
    
    # 最终进度报告
    total_time = time.time() - processor.start_time
    stats = processor.get_progress_stats()
    
    print_progress_report(processor, total_samples)
    
    # 构建最终结果摘要
    summary = {
        'total_samples': total_samples,
        'processed_samples': processor.processed_count,
        'successful_samples': processor.success_count,
        'failed_samples': processor.failed_count,
        'skipped_samples': processor.skipped_count,
        'success_rate': stats['success_rate'],
        'total_execution_time': total_time,
        'average_time_per_sample': total_time / max(processor.processed_count, 1),
        'samples_per_minute': stats['samples_per_minute'],
        'failed_sample_details': processor.failed_samples,
        'processing_config': {
            'num_threads': args.num_threads,
            'model_type': args.model_type,
            'max_steps': args.max_steps,
            'dataset_range': f"[{args.start_index}, {args.start_index + len(dataset)})"
        }
    }
    
    return {
        'summary': summary,
        'results': processor.results
    }

def generate_summary_report(batch_results: Dict[str, Any], 
                          output_path: str) -> None:
    """生成详细的执行摘要报告"""
    summary = batch_results['summary']
    results = batch_results['results']
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 生成JSON格式的详细报告
    detailed_report = {
        'batch_execution_summary': summary,
        'sample_results': results,
        'generated_at': datetime.now().isoformat(),
        'report_version': '1.0'
    }
    
    report_file = os.path.join(output_path, f'batch_report_{timestamp}.json')
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_report, f, ensure_ascii=False, indent=2)
        
        logging.info(f"详细报告已保存: {report_file}")
        
        # 生成人类可读的摘要
        summary_file = os.path.join(output_path, f'batch_summary_{timestamp}.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("AIM医疗问诊工作流批处理执行摘要\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总样本数: {summary['total_samples']}\n")
            f.write(f"处理样本数: {summary['processed_samples']}\n")
            f.write(f"成功样本数: {summary['successful_samples']}\n")
            f.write(f"失败样本数: {summary['failed_samples']}\n")
            f.write(f"跳过样本数: {summary['skipped_samples']}\n")
            f.write(f"成功率: {summary['success_rate']:.2%}\n")
            f.write(f"总执行时间: {summary['total_execution_time']:.2f} 秒\n")
            f.write(f"平均处理时间: {summary['average_time_per_sample']:.2f} 秒/样本\n")
            f.write(f"处理速度: {summary['samples_per_minute']:.2f} 样本/分钟\n\n")
            
            f.write("处理配置:\n")
            for key, value in summary['processing_config'].items():
                f.write(f"  {key}: {value}\n")
            
            if summary['failed_samples'] > 0:
                f.write(f"\n失败样本详情:\n")
                for failed in summary['failed_sample_details']:
                    f.write(f"  样本 {failed['sample_index']}: {failed['error']}\n")
        
        logging.info(f"摘要报告已保存: {summary_file}")
        
    except Exception as e:
        logging.error(f"生成报告失败: {e}")

def main():
    """主入口函数"""
    # 解析参数
    args = parse_arguments()

    # # 示例1：调试内科，并只处理2个样本
    # args.department_filter = '内科'
    # args.sample_limit = 2
    
    # 处理 --list-models 参数
    if args.list_models:
        print("可用的语言模型配置:")
        print("=" * 50)
        for model_name, config in LLM_CONFIG.items():
            print(f"模型名称: {model_name}")
            print(f"  类别: {config['class']}")
            print(f"  模型ID: {config['params']['id']}")
            print(f"  API端点: {config['params']['base_url']}")
            print("-" * 30)
        return 0
    
    # 设置日志
    setup_logging(args.batch_log_dir, args.log_level)
    
    logging.info("=" * 60)
    logging.info("AIM医疗问诊工作流批处理系统启动")
    logging.info("=" * 60)
    
    try:
        # 验证参数
        if args.num_threads <= 0:
            raise ValueError("线程数必须大于0")
        
        if args.max_steps <= 0:
            raise ValueError("最大步数必须大于0")
        
        # 验证模型类型
        if args.model_type not in LLM_CONFIG:
            available_models = ', '.join(LLM_CONFIG.keys())
            raise ValueError(f"不支持的模型类型: {args.model_type}，可用模型: {available_models}")
        
        logging.info(f"使用模型: {args.model_type} ({LLM_CONFIG[args.model_type]['class']})")
        
        # 试运行模式
        if args.dry_run:
            logging.info("试运行模式：验证配置...")
            dataset = load_dataset(
                args.dataset_path, 
                args.start_index, 
                args.end_index, 
                min(args.sample_limit or 5, 5)  # 试运行只验证前5个样本
            )
            logging.info(f"配置验证成功，将处理 {len(dataset)} 个样本")
            return 0
        
        # 加载数据集
        dataset = load_dataset(
            args.dataset_path, 
            args.start_index, 
            args.end_index, 
            args.sample_limit
        )
        
        # 如果指定了科室筛选，先筛选出指定科室的病例
        if args.department_filter:
            filtered_dataset = []
            for case in dataset:
                if case.get('一级科室', '') == args.department_filter:
                    filtered_dataset.append(case)
            dataset = filtered_dataset
            print(f"筛选 '{args.department_filter}' 科室病例: {len(dataset)} 个")

            #在固定科室模式下
            args.use_dynamic_guidance = False
            logging.info("固定科室模式已激活，动态指导已禁用。")

        total_cases = len(dataset)
        if total_cases == 0:
            logging.warning("没有样本需要处理")
            return 0
        
        # 打印初始化信息
        print(f"总共有 {total_cases} 个患者病例")
        if args.department_filter:
            print(f"筛选科室: {args.department_filter}")
        print(f"总共需要处理 {total_cases} 个患者病例")
        print(f"并行处理线程数: {args.num_threads}")
        print(f"结果将保存至 {args.output_dir} 目录")
        if args.use_inquiry_guidance:
            if args.department_filter:
                print(f"📋 已启用 '{args.department_filter}' 科室的固定询问指导")
            elif args.max_steps > 1:
                print(f"📋 已启用动态科室询问指导模式")
            else:
                print(f"📋 使用默认询问模式")
        else:
            print(f"📋 使用默认询问模式")
        
        if args.use_department_comparison:
            print(f"🔄 已启用科室对比鉴别功能")
        else:
            print(f"🔄 未启用科室对比鉴别功能")
        print("开始并行处理...\n")
        
        # 执行批处理
        logging.info("开始批量处理...")
        batch_results = run_workflow_batch(dataset, args)
        
        # 生成报告
        generate_summary_report(batch_results, args.output_dir)
        
        
        # 输出最终统计
        summary = batch_results['summary']
        logging.info("=" * 60)
        logging.info("批处理执行完成!")
        logging.info(f"成功率: {summary['success_rate']:.2%} ({summary['successful_samples']}/{summary['total_samples']})")
        logging.info(f"总耗时: {summary['total_execution_time']:.2f} 秒")
        logging.info(f"处理速度: {summary['samples_per_minute']:.2f} 样本/分钟")
        logging.info("=" * 60)
        
        # return 0 if summary['success_rate'] > 0.8 else 1
        return 0

    except KeyboardInterrupt:
        logging.warning("程序被用户中断")
        return 1
    except Exception as e:
        logging.error(f"程序执行失败: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)