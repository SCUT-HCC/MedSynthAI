import threading
import time
from datetime import datetime
import logging
from typing import Dict, Any

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