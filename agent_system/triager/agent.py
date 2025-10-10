from typing import Any
from agent_system.base import BaseAgent
from agent_system.triager.prompt import TriagerPrompt
from agent_system.triager.response_model import TriageResult


class TriageAgent(BaseAgent):
    """
    科室分诊智能体
    
    根据患者的现病史、既往史和主诉，分析症状特点，
    推荐最适合的一级科室和二级科室。
    
    核心功能:
    1. 分析患者症状涉及的主要器官系统
    2. 匹配合适的一级科室和二级科室
    3. 给出详细的分诊推理过程
    
    Attributes:
        model_type (str): 使用的大语言模型类型，默认为 gpt-oss:latest
        llm_config (dict): LLM模型配置参数
    """
    
    def __init__(self, model_type: str = "gpt-oss:latest", llm_config: dict = None):
        """
        初始化科室分诊智能体
        
        Args:
            model_type (str): 大语言模型类型，默认使用 gpt-oss:latest
            llm_config (dict): LLM模型的配置参数，如果为None则使用默认配置
        """
        super().__init__(
            model_type=model_type,
            description="根据患者病史信息进行科室分诊",
            instructions=TriagerPrompt.instructions,
            response_model=TriageResult,
            llm_config=llm_config or {},
            structured_outputs=True,
            markdown=False,
            use_cache=False
        )
    
    def run(self, chief_complaint: str, hpi_content: str = "", ph_content: str = "") -> TriageResult:
        """
        执行科室分诊
        
        基于患者的主诉、现病史和既往史信息，分析症状特点，
        推荐最适合的一级科室和二级科室。
        
        Args:
            chief_complaint (str): 患者主诉，描述主要症状和不适
            hpi_content (str, optional): 现病史内容，详细的症状发展过程，默认为空字符串
            ph_content (str, optional): 既往史内容，患者的历史疾病信息，默认为空字符串
            
        Returns:
            TriageResult: 包含分诊结果的结构化数据，包括：
                - primary_department: 推荐的一级科室
                - secondary_department: 推荐的二级科室
                - triage_reasoning: 分诊推理过程和建议理由
                
        Raises:
            Exception: 当LLM调用失败时，返回包含默认分诊建议的TriageResult
        """
        try:
            # 构建分诊分析提示词
            prompt = self.build_prompt(chief_complaint, hpi_content, ph_content)
            
            # 调用基类的run方法执行LLM推理
            result = super().run(prompt)
            
            # 确保返回正确的类型并进行类型转换
            return self._ensure_result_type(result)
            
        except Exception as e:
            # 当分诊分析失败时记录错误并返回默认结果
            print(f"科室分诊分析失败: {str(e)}")
            return self._get_fallback_result()
    
    def build_prompt(self, chief_complaint: str, hpi_content: str = "", ph_content: str = "") -> str:
        """
        构建科室分诊的提示词模板
        
        根据主诉、现病史和既往史内容，构建精简高效的分诊提示词，
        引导LLM进行专业的科室分诊分析。
        
        Args:
            chief_complaint (str): 患者主诉
            hpi_content (str): 现病史内容
            ph_content (str): 既往史内容
            
        Returns:
            str: 精简的分诊分析提示词
        """
        # 确保各项内容的合理显示
        hpi_display = hpi_content.strip() if hpi_content.strip() else "暂无详细现病史"
        ph_display = ph_content.strip() if ph_content.strip() else "暂无既往史信息"
        
        # 从prompt类获取示例输出格式
        example_output = TriagerPrompt.get_example_output()
        
        prompt = f"""患者就诊信息：
主诉: {chief_complaint}
现病史: {hpi_display}
既往史: {ph_display}

请根据上述患者信息，分析症状特点，推荐最适合的一级科室和二级科室。

输出格式示例：
{example_output}

请严格按照上述JSON格式输出，确保一级科室和二级科室的对应关系正确。
输出内容为:"""
        
        return prompt
    
    def _ensure_result_type(self, result: Any) -> TriageResult:
        """
        确保返回结果为正确的类型
        
        Args:
            result (Any): LLM返回的原始结果
            
        Returns:
            TriageResult: 转换后的结构化结果
        """
        if isinstance(result, TriageResult):
            return result
        elif isinstance(result, dict):
            return TriageResult(**result)
        else:
            # 如果类型不匹配，返回默认结果
            return self._get_fallback_result()
    
    def _get_fallback_result(self) -> TriageResult:
        """
        生成分诊失败时的默认结果
        
        Returns:
            TriageResult: 包含默认分诊建议的结果
        """
        return TriageResult(
            triage_reasoning="由于分诊分析过程中出现异常，系统推荐全科就诊。建议患者先到全科进行初步评估，医生会根据具体情况进一步转诊到合适的专科。",
            primary_department="全科",
            secondary_department="全科（二级）",
        )
    
    def triage_by_chief_complaint(self, chief_complaint: str) -> TriageResult:
        """
        仅基于患者主诉进行科室分诊的便捷接口
        
        这是一个专门针对仅有主诉信息的分诊方法，
        适用于患者初次就诊、信息较少的情况。
        
        Args:
            chief_complaint (str): 患者的主要症状主诉
            
        Returns:
            TriageResult: 基于主诉的分诊结果
        """
        return self.run(chief_complaint=chief_complaint, hpi_content="", ph_content="")
