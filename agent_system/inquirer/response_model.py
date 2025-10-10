from pydantic import Field
from agent_system.base.response_model import BaseResponseModel


class InquirerResponseModel(BaseResponseModel):
    """
    询问者智能体响应模型
    
    该模型用于封装询问者智能体生成的问诊问题，
    基于患者的现病史和既往史生成医生需要询问的具体问题。
    
    Attributes:
        current_chat (str): 当前生成的问诊问题内容
    """
    current_chat: str = Field(
        ...,
        description=(
            "基于患者现病史和既往史生成的医生问诊问题。"
            "问题应该针对性强、专业准确，有助于获取更多诊断相关信息。"
            "语言通俗易懂，符合医患交流的实际情况。"
        )
    )