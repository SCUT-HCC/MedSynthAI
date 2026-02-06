import argparse
import os
import sys

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import LLM_CONFIG 

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
        default='results/logs',
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
        default='results/batch_logs',
        help='批处理运行时日志保存目录'
    )
    # 执行参数
    parser.add_argument(
        '--num-threads', 
        type=int, 
        default=4,
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
        default=100,
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
        choices=['内科', '外科', '儿科', '妇产科', '皮肤科', '眼科', '耳鼻喉科', '骨科', '中医科'],
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
        default='deepseek',  #可选模型阅读config.py中的LLM_CONFIG
        help=f'使用的语言模型类型，可选: {", ".join(available_models)}'
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
        default='sequence',  #默认为normal模式
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
    
    return parser.parse_args()