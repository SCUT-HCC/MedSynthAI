from pydantic import BaseModel, Field
from agent_system.base.response_model import BaseResponseModel


class TriageVirtualPatientResponseModel(BaseModel):
    """
    虚拟患者分诊系统响应模型。
    
    该模型用于封装虚拟患者在分诊过程中生成的对话内容，
    确保响应的结构化和标准化。
    
    Attributes:
        current_chat (str): 虚拟患者当前轮次的对话回复内容
    """
    current_chat: str = Field(
        ...,
        description=(
            "虚拟患者对当前医护人员询问的对话回复。"
            "基于病历信息（主诉、现病史、既往史等）生成符合真实患者表达习惯的回答。"
            "严格遵循信息边界约束，不得添加或编造病历中未记录的内容。"
        )
    )
