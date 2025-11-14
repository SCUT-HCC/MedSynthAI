from typing import Dict, Any, List
from agent_system.base import BaseAgent
from agent_system.evaluator.prompt import EvaluatorPrompt
from agent_system.evaluator.response_model import EvaluatorResult


class Evaluator(BaseAgent):
    """
    评价器Agent
    
    专门用于评价智能医疗系统的多维度评价工具。
    从七个核心维度对智能医生的表现进行全面评价，
    包括当前轮次的表现和结合所有轮次的累积表现。
    
    核心功能:
    1. 临床问诊能力评价
    2. 沟通表达能力评价
    3. 多轮一致性评价
    4. 整体专业性评价
    5. 现病史相似度评价
    6. 既往史相似度评价
    7. 主述相似度评价
    
    Attributes:
        model_type (str): 使用的大语言模型类型，默认为 gpt-oss:latest
        llm_config (dict): LLM模型配置参数
    """
    
    def __init__(self, model_type: str = "gpt-oss:latest", llm_config: dict = None):
        """
        初始化评价器Agent
        
        Args:
            model_type (str): 大语言模型类型，默认使用 gpt-oss:latest
            llm_config (dict): LLM模型的配置参数，如果为None则使用默认配置
        """
        super().__init__(
            model_type=model_type,
            description=EvaluatorPrompt.description,
            instructions=EvaluatorPrompt.instructions,
            response_model=EvaluatorResult,
            llm_config=llm_config or {},
            structured_outputs=True,
            markdown=False,
            use_cache=False
        )
    
    def run(self, patient_case: Dict[str, Any], current_round: int, 
            all_rounds_data: List[Dict[str, Any]], historical_scores: Dict[str, float] = None) -> EvaluatorResult:
        """
        执行评价任务
        
        基于患者病例信息、当前轮次和所有轮次的对话数据（包含历史评分），
        对智能医疗系统进行多维度评价。
        
        Args:
            patient_case (Dict[str, Any]): 患者病例信息
            current_round (int): 当前轮次
            all_rounds_data (List[Dict[str, Any]]): 所有轮次的数据，每个轮次数据包含评分信息
            
        Returns:
            EvaluatorResult: 包含评价结果的结构化数据，包括：
                - clinical_inquiry: 临床问诊能力评价
                - communication_quality: 沟通表达能力评价
                - information_completeness: 信息收集全面性评价
                - overall_professionalism: 整体专业性评价
                - present_illness_similarity: 现病史相似度评价
                - past_history_similarity: 既往史相似度评价
                - chief_complaint_similarity: 主述相似度评价
                - summary: 整体评价总结
                - key_suggestions: 关键改进建议列表
                
        Raises:
            Exception: 当LLM调用失败时，返回包含默认信息的EvaluatorResult
        """
        try:
            # 构建评价提示词
            prompt = self.build_prompt(patient_case, current_round, all_rounds_data, historical_scores)
            
            # 调用基类的run方法执行LLM推理
            result = super().run(prompt)
            
            # 确保返回正确的类型并进行类型转换
            return self._ensure_result_type(result)
            
        except Exception as e:
            # 当评价失败时记录错误并返回默认结果
            print(f"评价执行失败: {str(e)}")
            return self._get_fallback_result()
    
    def build_prompt(self, patient_case: Dict[str, Any], current_round: int, 
                     all_rounds_data: List[Dict[str, Any]], historical_scores: Dict[str, float] = None) -> str:
        """
        构建评价的提示词模板
        
        根据患者病例信息、当前轮次和所有轮次数据（包含历史评分），
        构建简洁高效的评价提示词，引导LLM进行专业的医疗系统评价。
        
        Args:
            patient_case (Dict[str, Any]): 患者病例信息
            current_round (int): 当前轮次
            all_rounds_data (List[Dict[str, Any]]): 所有轮次的数据，包含对话记录和历史评分
            
        Returns:
            str: 精简的评价提示词
        """
        # 格式化患者信息
        patient_info = self._format_patient_info(patient_case)
        
        # 格式化真实病历信息
        true_medical_info = self._format_true_medical_info(patient_case)
        
        # 格式化对话历史
        conversation_history = self._format_conversation_history(all_rounds_data)
        
        # 获取示例输出格式
        example_output = EvaluatorPrompt.get_example_output()
        
        # 格式化历史评分信息
        historical_scores_info = ""
        if historical_scores:
            historical_scores_info = "\n**历史评分信息**:\n"
            for dimension, score in historical_scores.items():
                historical_scores_info += f"- {dimension}: {score}\n"

        prompt = f"""患者病例信息：
{patient_info}

真实病历信息（用于相似度比较）：
{true_medical_info}

对话历史（共{current_round}轮，包含每轮评分）：
{conversation_history}
{historical_scores_info}
请基于对话历史、现病史、既往史、主诉以及上述历史评分，对七个维度进行综合评价，
严格按照JSON格式输出。

输出格式示例：
{example_output}

请严格按照上述JSON格式输出评价结果。"""
        
        return prompt
    
    def _ensure_result_type(self, result: Any) -> EvaluatorResult:
        """
        确保返回结果为正确的类型
        
        Args:
            result (Any): LLM返回的原始结果
            
        Returns:
            EvaluatorResult: 转换后的结构化结果
        """
        if isinstance(result, EvaluatorResult):
            return result
        elif isinstance(result, dict):
            return EvaluatorResult(**result)
        else:
            # 如果类型不匹配，返回默认结果
            return self._get_fallback_result()
    
    def _get_fallback_result(self) -> EvaluatorResult:
        """
        生成评价失败时的默认结果
        
        Returns:
            EvaluatorResult: 包含默认评价信息的结果
        """
        from agent_system.evaluator.response_model import EvaluationDimension
        
        default_dimension = EvaluationDimension(
            score=0.0, 
            comment="评价失败：系统异常，无法完成评价"
        )
        
        return EvaluatorResult(
            clinical_inquiry=default_dimension,
            communication_quality=default_dimension,
            information_completeness=default_dimension,
            overall_professionalism=default_dimension,
            present_illness_similarity=default_dimension,
            past_history_similarity=default_dimension,
            chief_complaint_similarity=default_dimension,
            summary="评价失败：系统异常，无法完成评价",
            key_suggestions=["系统需要调试和修复"]
        )
    
    def _format_patient_info(self, patient_case: Dict[str, Any]) -> str:
        """格式化患者信息"""
        info_parts = []
        
        # 病案信息
        if '病案介绍' in patient_case:
            case_info = patient_case['病案介绍']
            
            if '基本信息' in case_info:
                info_parts.append(f"**基本信息**: {case_info['基本信息']}")
            
            if '主诉' in case_info:
                info_parts.append(f"**主诉**: {case_info['主诉']}")
            
            if '现病史' in case_info:
                info_parts.append(f"**现病史**: {case_info['现病史']}")
            
            if '既往史' in case_info:
                info_parts.append(f"**既往史**: {case_info['既往史']}")
        
        return '\n'.join(info_parts)
    
    def _format_true_medical_info(self, patient_case: Dict[str, Any]) -> str:
        """格式化真实病历信息，用于相似度比较"""
        info_parts = []
        
        # 病案信息
        if '病案介绍' in patient_case:
            case_info = patient_case['病案介绍']
            
            if '主诉' in case_info:
                info_parts.append(f"**真实主诉**: {case_info['主诉']}")
            
            if '现病史' in case_info:
                info_parts.append(f"**真实现病史**: {case_info['现病史']}")
            
            if '既往史' in case_info:
                info_parts.append(f"**真实既往史**: {case_info['既往史']}")
        
        return '\n'.join(info_parts)
    

    def _format_conversation_history(self, all_rounds_data: List[Dict[str, Any]]) -> str:
        """格式化对话历史，包含每轮的对话记录和评分"""
        history_parts = []
        
        for i, round_data in enumerate(all_rounds_data, 1):
            if i < len(all_rounds_data):
                continue
            history_parts.append(f"### 第{i}轮对话")
            
            if 'patient_response' in round_data:
                history_parts.append(f"**患者回答**: {round_data['patient_response']}")
            
            if 'doctor_inquiry' in round_data:
                history_parts.append(f"**医生询问**: {round_data['doctor_inquiry']}")
            
            if 'HPI' in round_data:
                history_parts.append(f"**现病史(HPI)**: {round_data['HPI']}")
            
            if 'PH' in round_data:
                history_parts.append(f"**既往史(PH)**: {round_data['PH']}")
            
            if 'chief_complaint' in round_data:
                history_parts.append(f"**主述(CC)**: {round_data['chief_complaint']}")
            
            # 添加该轮的评分信息
            if 'evaluation_scores' in round_data:
                scores = round_data['evaluation_scores']
                history_parts.append("**该轮评分**:")
                history_parts.append(f"- 临床问诊能力: {scores.get('clinical_inquiry', 'N/A')}/5")
                history_parts.append(f"- 沟通表达能力: {scores.get('communication_quality', 'N/A')}/5")
                history_parts.append(f"- 信息收集全面性: {scores.get('information_completeness', scores.get('multi_round_consistency', 'N/A'))}/5")
                history_parts.append(f"- 整体专业性: {scores.get('overall_professionalism', 'N/A')}/5")
                history_parts.append(f"- 现病史相似度: {scores.get('present_illness_similarity', 'N/A')}/5")
                history_parts.append(f"- 既往史相似度: {scores.get('past_history_similarity', 'N/A')}/5")
                history_parts.append(f"- 主述相似度: {scores.get('chief_complaint_similarity', 'N/A')}/5")
            
            history_parts.append("")  # 空行分隔
        
        return '\n'.join(history_parts)
    
    def evaluate_single_round(self, patient_case: Dict[str, Any], 
                             round_data: Dict[str, Any]) -> EvaluatorResult:
        """
        评价单轮对话的便捷接口
        
        Args:
            patient_case (Dict[str, Any]): 患者病例信息
            round_data (Dict[str, Any]): 单轮对话数据
            
        Returns:
            EvaluatorResult: 单轮评价结果
        """
        return self.run(patient_case, 1, [round_data])