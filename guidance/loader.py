# 负责读取、解析并缓存这些指导文件。
# 它对外提供简洁的函数接口（如get_comparison_guidance_data()），供Agent调用。

import json
import os
from typing import Dict, Any, List, Optional, Union
import time


class GuidanceLoader:
    """
    指导加载器类，负责加载、缓存和提供指导数据
    
    实现了单例模式，确保整个系统中只有一个加载器实例，减少重复加载
    支持缓存，避免频繁读取文件系统
    提供统一的接口，未来可以平滑迁移到数据库或知识图谱
    """
    
    _instance = None  # 单例实例
    
    # 默认文件路径配置
    DEFAULT_PATHS = {
        "comparison_guidance": "department_comparison_guidance.json",
        "inquiry_guidance": "department_inquiry_guidance.json"
    }
    
    # 缓存过期时间(秒)
    CACHE_TTL = 300  # 5分钟
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(GuidanceLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, base_path: str = None):
        """
        初始化指导加载器
        
        Args:
            base_path: 指导文件所在的基础路径，如果为None，则使用当前脚本所在目录
        """
        if self._initialized:
            return
            
        # 确定基础路径
        self.base_path = base_path or os.path.dirname(os.path.abspath(__file__))
        
        # 初始化缓存
        self._cache = {}
        self._cache_timestamp = {}
        
        # 初始化文件路径
        self.file_paths = {}
        for key, file_name in self.DEFAULT_PATHS.items():
            self.file_paths[key] = os.path.join(self.base_path, file_name)
        
        self._initialized = True
    
    def _load_comparison_rules(self):
        """加载科室对比鉴别规则"""
        try:
            rules_file = "department_comparison_rules.json"
            if os.path.exists(rules_file):
                with open(rules_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"⚠️ 科室对比规则文件不存在: {rules_file}")
                return {}
        except Exception as e:
            print(f"❌ 加载科室对比规则时出错: {e}")
            return {}
    
    def _get_comparison_guidance(self, dept1: str, dept2: str):
        """获取两个科室的对比鉴别指导"""
        if not self.comparison_rules:
            return ""
        
        guidance_parts = []
        
        # 1. 获取科室对比规则
        # 提取二级科室
        def extract_secondary(dept):
            return dept.split('-')[1] if '-' in dept else dept
        
        def extract_primary(dept):
            return dept.split('-')[0] if '-' in dept else dept
        
        sec1 = extract_secondary(dept1)
        sec2 = extract_secondary(dept2)
        
        # 尝试多种组合方式查找对比规则
        possible_keys = [
            f"{sec1}|{sec2}",
            f"{sec2}|{sec1}",
            f"{dept1}|{dept2}", 
            f"{dept2}|{dept1}"
        ]
        
        for key in possible_keys:
            if key in self.comparison_rules:
                rules = self.comparison_rules[key]
                guidance_text = f"【{rules['description']}】\n"
                guidance_text += "\n".join([f"- {rule}" for rule in rules['rules']])
                guidance_parts.append(guidance_text)
                break
        
        # 2. 获取一级科室的单体指导
        primary1 = extract_primary(dept1)
        primary2 = extract_primary(dept2)
        
        # 为主科室添加单体指导
        if primary1 in self.comparison_rules:
            primary1_rules = self.comparison_rules[primary1]
            guidance_text = f"【{primary1}科室选择指导】\n"
            guidance_text += "\n".join([f"- {rule}" for rule in primary1_rules['rules']])
            guidance_parts.append(guidance_text)
        
        # 为候选科室添加单体指导（如果不同一级科室）
        if primary2 != primary1 and primary2 in self.comparison_rules:
            primary2_rules = self.comparison_rules[primary2]
            guidance_text = f"【{primary2}科室选择指导】\n"
            guidance_text += "\n".join([f"- {rule}" for rule in primary2_rules['rules']])
            guidance_parts.append(guidance_text)
        
        return "\n\n".join(guidance_parts)
    
    def _update_guidance_for_Triager(self, predicted_department: str):
        """根据预测的科室动态更新询问指导"""
        if not self.use_dynamic_guidance or not self.load_guidance_func:
            return
        
        # 提取一级科室
        first_department = predicted_department.split('-')[0] if '-' in predicted_department else predicted_department
        
        # 加载新的指导
        new_guidance = self.load_guidance_func(first_department)

        return new_guidance
        
