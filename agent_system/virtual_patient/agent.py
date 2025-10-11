from typing import Dict, Any
from config import LLM_CONFIG
from agent_system.base import BaseAgent
from agent_system.virtual_patient.response_model import TriageVirtualPatientResponseModel
from agent_system.virtual_patient.prompt import TriageVirtualPatientPrompt


class VirtualPatientAgent(BaseAgent):
    """
    虚拟患者智能体类，用于模拟真实患者在分诊过程中的自然对话行为。
    
    主要功能：
    - 基于病历信息生成符合真实患者表达习惯的对话
    - 严格控制信息边界，仅基于病历记录回答问题
    - 支持首轮主诉和后续问诊的不同对话模式
    - 渐进式信息提供，避免信息过载
    
    Attributes:
        model_type (str): 使用的大语言模型类型，默认为 gpt-oss:latest
        llm_config (dict): LLM模型配置参数
    """
    def __init__(self, model_type: str = "gpt-oss:latest", llm_config: dict = None):
        """
        初始化虚拟患者智能体。
        
        Args:
            model_type (str): 大语言模型类型，默认使用 gpt-oss:latest
            llm_config (dict): LLM模型的配置参数，如果为None则使用默认配置
        """
        super().__init__(
            model_type=model_type,
            description=TriageVirtualPatientPrompt.description,
            instructions=TriageVirtualPatientPrompt.instructions,
            response_model=TriageVirtualPatientResponseModel,
            llm_config=llm_config or {},
            structured_outputs=True,
            markdown=False,
            use_cache=False
        )

    def run(
        self,
        worker_inquiry: str,
        is_first_epoch: bool,
        patient_case: Dict[str, Any] = None,
        **kwargs
    ) -> TriageVirtualPatientResponseModel:
        """
        运行虚拟患者智能体，生成对话回复。
        
        Args:
            worker_inquiry (str): 医护人员的询问内容
            is_first_epoch (bool): 是否为首轮对话
            patient_case (Dict[str, Any], optional): 患者病历信息
            
        Returns:
            TriageVirtualPatientResponseModel: 包含虚拟患者对话回复的响应模型
        """

        prompt = self._build_prompt(worker_inquiry, is_first_epoch, patient_case)
        return super().run(prompt, **kwargs)
        


    async def async_run(
        self,
        worker_inquiry: str,
        is_first_epoch: bool,
        patient_case: Dict[str, Any] = None,
        **kwargs
    ) -> TriageVirtualPatientResponseModel:
        """
        异步运行虚拟患者智能体，生成对话回复。
        
        Args:
            worker_inquiry (str): 医护人员的询问内容
            is_first_epoch (bool): 是否为首轮对话
            patient_case (Dict[str, Any], optional): 患者病历信息
            
        Returns:
            TriageVirtualPatientResponseModel: 包含虚拟患者对话回复的响应模型
        """
        prompt = self._build_prompt(worker_inquiry, is_first_epoch, patient_case)
        return await super().async_run(prompt, **kwargs)


    def _build_prompt(
        self,
        worker_inquiry: str,
        is_first_epoch: bool,
        patient_case: Dict[str, Any] = None
    ) -> str:
        """
        构建虚拟患者对话的动态提示词。
        
        根据对话轮次（首轮/后续）和病历信息生成相应的提示词，
        确保虚拟患者仅基于病历记录进行回答。
        
        Args:
            worker_inquiry (str): 医护人员的询问内容
            is_first_epoch (bool): 是否为首轮对话
            patient_case (Dict[str, Any], optional): 患者病历信息
            
        Returns:
            str: 构建完成的动态提示词
        """
        if patient_case is None:
            patient_case = {}

        # 第一部分：从病历中提取关键信息（严格限制信息范围）
        # 提取病历各个字段，确保信息的完整性和准确性
        case_info = patient_case.get("病案介绍", {})
        basic_info = case_info.get("基本信息", "").strip()
        chief_complaint = case_info.get("主诉", "").strip()
        history_details = case_info.get("现病史", "").strip()
        past_history = case_info.get("既往史", "").strip()
        
        # 构建病历背景信息（严格限定信息范围）
        medical_context = (
            "【唯一可用病历信息 - 不得超出此范围】\n"
            f"基本信息：{basic_info}\n"
            f"主诉：{chief_complaint}\n"
            f"现病史：{history_details}\n"
            f"既往史：{past_history if past_history else '无'}\n"
            "\n【重要提醒】以上即为全部可用信息，不得添加任何未明确记录的内容\n"
        )
        
        # 第二部分：根据对话阶段生成相应的场景提示词
        if is_first_epoch:
            # 首轮对话prompt
            scenario_prompt = (
                "【首轮对话】\n"
                "你是一位前来就诊的虚拟患者，刚到分诊台。\n"
                "仅基于上述基本信息和主诉内容，用1-2句话描述最主要的不适症状。\n"
                f"参考示例：'医生您好，我今年18岁了，最近三天头一直痛' \n"
                "\n**首轮严格约束**：\n"
                "- 仅能描述主诉和基本信息中明确记录的内容\n"
                "- 禁止添加任何时间、程度、部位等未记录的细节\n"
                "- 禁止描述现病史中的具体情况\n\n"
                "输出格式示例：\n"
                f"{TriageVirtualPatientPrompt.get_example_output()}\n\n"
                "请严格按照上JSON格式输出。"
            )
        else:
            # 后续对话prompt
            scenario_prompt = (
                "【后续对话】\n"
                f"护士/医生询问：「{worker_inquiry}」\n"
                "请根据你的病历信息如实回答这个问题。\n\n"
                "**严格回答原则 - 禁止虚构任何信息**：\n"
                "1. 【核心约束】仅能基于上述病历信息回答，严禁编造任何内容\n"
                "2. 【信息边界】病历未提及的内容一律回答'没有'、'无'、'从来没有'\n"
                "3. 【不确定处理】模糊记忆用'记不清了'、'不太确定'表达\n"
                "4. 【直接回应】禁止回避问题，必须针对性回答\n"
                "5. 【禁止推测】不能基于症状推测其他可能的病症或情况\n\n"
                "**否定回答示例**：\n"
                "- 询问既往疾病：'没有，我身体一直很好'\n"
                "- 询问手术史：'没有做过手术'\n"
                "- 询问过敏史：'没有，我不过敏'\n"
                "- 询问家族史：'家里人都挺健康的，没有这方面的病'\n"
                "- 询问用药史：'这是第一次出现这种情况，之前没吃过药'\n\n"
                "回答要自然真实，用1-3句话即可。\n\n"
                "输出格式示例：\n"
                f"{TriageVirtualPatientPrompt.get_example_output()}\n\n"
                "请严格按照上JSON格式输出。"
            )
        
        # 组合病历信息和场景提示，形成完整的动态提示词
        return f"{medical_context}\n{scenario_prompt}"

