from agent_system.base import BaseAgent
from agent_system.recipient.prompt import RecipientPrompt
from agent_system.recipient.response_model import RecipientResponseModel

class RecipientAgent(BaseAgent):
    """Recipient智能体：根据完整对话记录和上一轮医疗信息，更新现病史、既往史并提取主诉"""
    
    def __init__(self, model_type: str, llm_config: dict = {}):
        super().__init__(
            model_type=model_type,
            description=RecipientPrompt.description,
            instructions=RecipientPrompt.instructions,
            response_model=RecipientResponseModel,
            llm_config=llm_config,
            structured_outputs=True,
            markdown=False,
            use_cache=False,
        )

    def run(
        self,
        conversation_history: str,
        previous_HPI: str = None,
        previous_PH: str = None,
        previous_chief_complaint: str = None,
        **kwargs
    ) -> RecipientResponseModel:
        """运行Recipient智能体
        
        Args:
            conversation_history: 完整的对话记录
            previous_HPI: 上一轮的现病史
            previous_PH: 上一轮的既往史
            previous_chief_complaint: 上一轮的主诉（可选，用于参考）
            
        Returns:
            RecipientResponseModel: 包含更新后的主诉、现病史和既往史
        """
        prompt = self.build_prompt(
            conversation_history, 
            previous_HPI, 
            previous_PH, 
            previous_chief_complaint
        )
        return super().run(prompt, **kwargs)
    
    async def async_run(
        self,
        conversation_history: str,
        previous_HPI: str = None,
        previous_PH: str = None,
        previous_chief_complaint: str = None,
        **kwargs
    ) -> RecipientResponseModel:
        """异步运行Recipient智能体"""
        prompt = self.build_prompt(
            conversation_history, 
            previous_HPI, 
            previous_PH, 
            previous_chief_complaint
        )
        return await super().async_run(prompt, **kwargs)

    def build_prompt(
        self, 
        conversation_history: str, 
        previous_HPI: str, 
        previous_PH: str,
        previous_chief_complaint: str = None
    ) -> str:
        """构建处理提示"""
        prompt = f"完整对话记录：\n{conversation_history}\n\n"
        
        prompt += f"上一轮的现病史：\n{previous_HPI or '暂无现病史信息'}\n\n"
        
        prompt += f"上一轮的既往史：\n{previous_PH or '暂无既往史信息'}\n\n"
        
        if previous_chief_complaint:
            prompt += f"上一轮的主诉（参考）：\n{previous_chief_complaint}\n\n"
        
        prompt += f"请根据完整对话记录和上一轮的医疗信息，完成以下任务（按此顺序生成）：\n"
        prompt += f"1. 根据完整对话记录和上一轮现病史，更新并完善现病史（updated_HPI）\n"
        prompt += f"2. 根据完整对话记录和上一轮既往史，更新并完善既往史（updated_PH）\n"
        prompt += f"3. 从完整对话记录中提取患者的主诉（chief_complaint）"
        
        return prompt