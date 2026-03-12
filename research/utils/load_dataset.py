import os
import json
import logging
from typing import List, Dict, Any, Optional
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
