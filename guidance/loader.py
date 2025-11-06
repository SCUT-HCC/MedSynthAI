import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GuidanceLoader:
    def __init__(self, 
                 department_guidance: str = "",
                 use_dynamic_guidance: bool = False,  
                 use_department_comparison: bool = False, 
                 department_guidance_file: str = "",
                 comparison_rules_file: str = ""
                ) -> None:
        """初始化指导规则加载器"""
        self.use_dynamic_guidance = use_dynamic_guidance
        self.use_department_comparison = use_department_comparison
        self.department_guidance_file = department_guidance_file
        self.comparison_rules_file = comparison_rules_file

        self.current_guidance = department_guidance
        self.comparison_rules = self._load_comparison_rules() if self.use_department_comparison else {}

    def _load_comparison_rules(self) -> Dict[str, Any]:
        """加载科室对比规则"""
        try:
            if os.path.exists(self.comparison_rules_file):
                with open(self.comparison_rules_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"⚠️ 科室对比规则文件不存在: {self.comparison_rules_file}")
                return {}
        except Exception as e:
            logger.error(f"❌ 加载科室对比规则时出错: {e}")
            return {}
    
    def load_inquiry_guidance(self, department: str) -> str:
        """加载科室特定的询问指导"""
        try:
            guidance_file = self.department_guidance_file
            
            if not os.path.exists(guidance_file):
                logger.warning(f"⚠️ 指导文件不存在: {guidance_file}")
                return ""
            
            with open(guidance_file, 'r', encoding='utf-8') as f:
                guidance_data = json.load(f)
            
            if department not in guidance_data:
                if "其他" in guidance_data:
                    logger.warning(f"⚠️ 未找到 '{department}' 科室的特定询问指导，使用通用指导")
                    department = "其他"
                else:
                    logger.warning(f"⚠️ 未找到 '{department}' 科室的询问指导，也没有通用指导")
                    return ""
            
            guidance_list = guidance_data[department]
            guidance_text = "\n".join([f"- {item}" for item in guidance_list])
            return guidance_text
        
        except Exception as e:
            logger.error(f"❌ 加载询问指导时出错: {e}")
            return ""
    
    # 添加公共方法接口（重要！）
    def get_comparison_guidance(self, dept1: str, dept2: str) -> str:
        """公共方法：获取两个科室的对比鉴别指导"""
        return self._get_comparison_guidance(dept1, dept2)
    
    def update_guidance_for_Triager(self, predicted_department: str) -> str:
        """公共方法：动态更新询问指导（注意大小写！）"""
        return self._update_guidance_for_Triager(predicted_department)
    
    # 如果需要小写版本，也可以添加
    def update_guidance_for_triager(self, predicted_department: str) -> str:
        """公共方法：动态更新询问指导（小写版本）"""
        return self._update_guidance_for_Triager(predicted_department)
    
    # 私有方法实现        
    def _get_comparison_guidance(self, dept1: str, dept2: str) -> str:
        """获取两个科室的对比鉴别指导"""
        if not self.comparison_rules:
            return ""
        
        guidance_parts = []
        
        # 提取二级科室
        def extract_secondary(dept: str) -> str:
            return dept.split('-')[1] if '-' in dept else dept
        
        def extract_primary(dept: str) -> str:
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
        
        # 获取一级科室的单体指导
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
    
    def _update_guidance_for_Triager(self, predicted_department: str) -> str:
        """动态更新询问指导。如果禁用动态指导，则返回当前的指导。"""
        # 修复：如果禁用了动态指导，则直接返回当前已有的指导，不进行任何更新
        if not self.use_dynamic_guidance:
            return self.department_guidance  
        
        first_department = predicted_department.split('-')[0] if '-' in predicted_department else predicted_department
        new_guidance = self.load_inquiry_guidance(first_department)
        
        if new_guidance and new_guidance != self.current_guidance:
            self.current_guidance = new_guidance
            logger.info(f"🔄 已切换到 '{first_department}' 科室的询问指导")
        
        return self.current_guidance