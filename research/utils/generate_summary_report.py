import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
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