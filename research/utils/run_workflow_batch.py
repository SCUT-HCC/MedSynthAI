import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import argparse

from utils.update_progress import BatchProcessor 
from utils.print_progress_report import print_progress_report 
from utils.is_case_completed import is_case_completed 
from utils.process_single_sample import process_single_sample  


def run_workflow_batch(dataset: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    """执行批量工作流处理"""
    total_samples = len(dataset)
    logging.info(f"使用 {args.num_threads} 个线程")
    
    # 创建批处理管理器
    processor = BatchProcessor(num_threads=args.num_threads)
    processor.start_time = time.time()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    
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