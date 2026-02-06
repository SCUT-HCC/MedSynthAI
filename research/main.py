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
from utils.update_progress import BatchProcessor
from utils.is_case_completed import is_case_completed
from utils.parse_arguments import parse_arguments
from utils.process_single_sample import process_single_sample
from utils.load_dataset import load_dataset
from utils.setup_logging import setup_logging
from utils.generate_summary_report import generate_summary_report
from utils.run_workflow_batch import run_workflow_batch
from utils.print_progress_report import print_progress_report

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from guidance.loader import GuidanceLoader

def main():
    """主入口函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志
    setup_logging(args.batch_log_dir, args.log_level)


    logging.info("=" * 60)
    logging.info("AIM医疗问诊工作流批处理系统启动")
    logging.info("=" * 60)
    
    try:
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
        
        # 打印初始化信息
        if args.department_filter:
            print(f"筛选科室: {args.department_filter}")
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