from utils.update_progress import BatchProcessor
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