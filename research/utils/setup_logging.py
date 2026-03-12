import os
import logging
from datetime import datetime
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