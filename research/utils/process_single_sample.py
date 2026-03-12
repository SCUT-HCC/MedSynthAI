import argparse
import os
import json
import sys
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any
from datetime import datetime
from utils.update_progress import BatchProcessor

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from research.workflow import MedicalWorkflow
from config import LLM_CONFIG 
from guidance.loader import GuidanceLoader


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