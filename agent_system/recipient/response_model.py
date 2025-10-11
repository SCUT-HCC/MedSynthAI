from pydantic import Field
from agent_system.base import BaseResponseModel

class RecipientResponseModel(BaseResponseModel):
    """Recipient智能体响应模型"""
    
    updated_HPI: str = Field(
        ...,
        description="更新后的现病史，根据完整对话记录和上一轮现病史进行整合更新"
    )
    
    updated_PH: str = Field(
        ...,
        description="更新后的既往史，根据完整对话记录和上一轮既往史进行整合更新"
    )
    
    chief_complaint: str = Field(
        ...,
        description="根据完整对话记录提取的患者主诉，简洁描述患者的主要症状及持续时间"
    )