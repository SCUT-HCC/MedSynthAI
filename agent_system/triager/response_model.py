from typing import Literal
from pydantic import Field
from agent_system.base import BaseResponseModel


class TriageResult(BaseResponseModel):
    """
    科室分诊结果模型
    """
    triage_reasoning: str = Field(
        ...,
        description="分诊推理过程，解释为什么推荐该科室"
    )
    
    primary_department: Literal[
        "内科", "外科", "儿科", "妇产科", "皮肤性病科", 
        "口腔科", "眼科", "肿瘤科", "耳鼻咽喉科", "康复科", 
        "精神科", "全科", "体检科"
    ] = Field(
        ...,
        description="一级科室，必须从指定的科室列表中选择"
    )
    
    secondary_department: str = Field(
        ...,
        description="二级科室，必须是一级科室的下属科室"
    )