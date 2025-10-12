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
    
    def _should_reload(self, cache_key: str) -> bool:
        """
        检查是否应该重新加载缓存
        
        Args:
            cache_key: 缓存键名
            
        Returns:
            bool: 如果应该重新加载返回True，否则返回False
        """
        # 如果缓存中没有数据，需要加载
        if cache_key not in self._cache:
            return True
            
        # 如果文件被修改，需要重新加载
        file_path = self.file_paths.get(cache_key)
        if not file_path or not os.path.exists(file_path):
            return False
            
        # 检查文件修改时间是否晚于缓存时间
        file_mtime = os.path.getmtime(file_path)
        cache_time = self._cache_timestamp.get(cache_key, 0)
        if file_mtime > cache_time:
            return True
            
        # 检查缓存是否过期
        current_time = time.time()
        if current_time - cache_time > self.CACHE_TTL:
            return True
            
        return False
    
    def _load_json_file(self, file_path: str) -> Dict[str, Any]:
        """
        从JSON文件加载数据
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            Dict: 加载的JSON数据
            
        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON格式错误
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON文件格式错误 ({file_path}): {e.msg}", e.doc, e.pos)
        except Exception as e:
            raise Exception(f"加载文件时出错 ({file_path}): {str(e)}")
    
    def get_comparison_guidance_data(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        获取所有科室对比鉴别指导的数据
        
        Args:
            force_reload: 是否强制重新加载，不使用缓存
            
        Returns:
            Dict: 科室对比鉴别指导数据
        """
        cache_key = "comparison_guidance"
        
        if force_reload or self._should_reload(cache_key):
            try:
                file_path = self.file_paths.get(cache_key)
                self._cache[cache_key] = self._load_json_file(file_path)
                self._cache_timestamp[cache_key] = time.time()
            except Exception as e:
                # 如果加载失败但有缓存，使用旧缓存
                if cache_key in self._cache:
                    print(f"⚠️ 重新加载对比指导失败，使用缓存: {e}")
                else:
                    print(f"❌ 加载对比指导失败，返回空数据: {e}")
                    self._cache[cache_key] = {}
                    self._cache_timestamp[cache_key] = time.time()
        
        return self._cache[cache_key]
    
    def get_inquiry_guidance_data(self, department: str = None, force_reload: bool = False) -> Union[str, Dict]:
        """
        获取科室询问指导
        
        Args:
            department: 科室名称。如果为None，返回所有科室的指导字典。
                        如果指定科室，返回该科室的格式化指导文本。
            force_reload: 是否强制重新加载，不使用缓存
            
        Returns:
            Union[str, Dict]: 如果指定了科室，返回该科室的询问指导文本；否则返回所有科室的指导字典。
        """
        cache_key = "inquiry_guidance"
        
        if force_reload or self._should_reload(cache_key):
            try:
                file_path = self.file_paths.get(cache_key)
                self._cache[cache_key] = self._load_json_file(file_path)
                self._cache_timestamp[cache_key] = time.time()
            except Exception as e:
                # 如果加载失败但有缓存，使用旧缓存
                if cache_key in self._cache:
                    print(f"⚠️ 重新加载询问指导失败，使用缓存: {e}")
                else:
                    print(f"❌ 加载询问指导失败，返回空数据: {e}")
                    self._cache[cache_key] = {}
                    self._cache_timestamp[cache_key] = time.time()
        
        all_guidance = self._cache[cache_key]

        # 如果未指定科室，返回所有指导
        if department is None:
            return all_guidance
        
        # 如果指定了科室，但找不到对应指导，尝试使用"其他"科室指导
        if department not in all_guidance:
            if "其他" in all_guidance:
                print(f"⚠️ 未找到 '{department}' 科室的特定询问指导，使用通用指导")
                department = "其他"
            else:
                print(f"⚠️ 未找到 '{department}' 科室的询问指导，也没有通用指导")
                return ""
        
        # 将指导列表转换为文本格式
        guidance_list = all_guidance.get(department, [])
        guidance_text = "\n".join([f"- {item}" for item in guidance_list])
        
        return guidance_text
    
    def get_comparison_guidance(self, dept1: str, dept2: str) -> str:
        """
        获取两个科室的对比鉴别指导文本
        
        Args:
            dept1: 第一个科室名称
            dept2: 第二个科室名称
            
        Returns:
            str: 对比鉴别指导文本
        """
        all_guidance = self.get_comparison_guidance_data()
        if not all_guidance:
            return ""
        
        guidance_parts = []
        
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
            if key in all_guidance:
                guidance_item = all_guidance[key]
                guidance_text = f"【{guidance_item['description']}】\n"
                guidance_text += "\n".join([f"- {rule}" for rule in guidance_item['rules']])
                guidance_parts.append(guidance_text)
                break
        
        # 获取一级科室的单体指导
        primary1 = extract_primary(dept1)
        primary2 = extract_primary(dept2)
        
        # 为主科室添加单体指导
        if primary1 in all_guidance:
            primary1_guidance = all_guidance[primary1]
            guidance_text = f"【{primary1}科室选择指导】\n"
            guidance_text += "\n".join([f"- {rule}" for rule in primary1_guidance['rules']])
            guidance_parts.append(guidance_text)
        
        # 为候选科室添加单体指导（如果不同一级科室）
        if primary2 != primary1 and primary2 in all_guidance:
            primary2_guidance = all_guidance[primary2]
            guidance_text = f"【{primary2}科室选择指导】\n"
            guidance_text += "\n".join([f"- {rule}" for rule in primary2_guidance['rules']])
            guidance_parts.append(guidance_text)
        
        return "\n\n".join(guidance_parts)
    
    def set_file_path(self, key: str, file_path: str) -> None:
        """
        设置特定指导文件的路径
        
        Args:
            key: 指导类型键名 ('comparison_guidance' 或 'inquiry_guidance')
            file_path: 文件路径
        """
        self.file_paths[key] = file_path
        # 清除相关缓存，确保下次重新加载
        if key in self._cache:
            del self._cache[key]
        if key in self._cache_timestamp:
            del self._cache_timestamp[key]


# 创建单例实例，方便直接导入使用
loader = GuidanceLoader()

# --- 对外提供的简洁接口函数 ---

def get_comparison_guidance_data(force_reload: bool = False) -> Dict[str, Any]:
    """
    获取所有科室对比鉴别指导的数据
    
    Args:
        force_reload: 是否强制重新加载，不使用缓存
        
    Returns:
        Dict: 科室对比鉴别指导数据
    """
    return loader.get_comparison_guidance_data(force_reload)

def get_inquiry_guidance(department: str = None, force_reload: bool = False) -> Union[str, Dict]:
    """
    获取科室询问指导
    
    Args:
        department: 科室名称。如果为None，返回所有科室的指导字典。
                    如果指定科室，返回该科室的格式化指导文本。
        force_reload: 是否强制重新加载，不使用缓存
        
    Returns:
        Union[str, Dict]: 如果指定了科室，返回该科室的询问指导文本；否则返回所有科室的指导字典。
    """
    return loader.get_inquiry_guidance_data(department, force_reload)

def get_comparison_guidance(dept1: str, dept2: str) -> str:
    """
    获取两个科室的对比鉴别指导文本
    
    Args:
        dept1: 第一个科室名称
        dept2: 第二个科室名称
        
    Returns:
        str: 对比鉴别指导文本
    """
    return loader.get_comparison_guidance(dept1, dept2)

def set_guidance_base_path(base_path: str) -> None:
    """
    设置指导文件的基础路径
    
    Args:
        base_path: 基础路径
    """
    global loader
    loader = GuidanceLoader(base_path)

def set_guidance_file_path(guidance_type: str, file_path: str) -> None:
    """
    设置特定指导文件的路径
    
    Args:
        guidance_type: 指导类型 ('comparison_guidance' 或 'inquiry_guidance')
        file_path: 文件路径
    """
    loader.set_file_path(guidance_type, file_path)