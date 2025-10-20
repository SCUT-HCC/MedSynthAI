from typing import Literal, Optional, Dict
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
    
    # 定义一级科室列表，方便复用
    PRIMARY_DEPARTMENTS = Literal[
        "内科", "外科", "儿科", "妇产科", "皮肤性病科", 
        "口腔科", "眼科", "肿瘤科", "耳鼻咽喉科", "康复科", 
        "精神科", "全科", "体检科"
    ]
    
    # 主要推荐科室
    primary_department: PRIMARY_DEPARTMENTS = Field(
        ...,
        description="推荐的一级科室，必须从指定的科室列表中选择"
    )
    
    secondary_department: str = Field(
        ...,
        description="推荐的二级科室，必须是一级科室的下属科室"
    )

    # 候选科室
    candidate_primary_department: Optional[PRIMARY_DEPARTMENTS] = Field(
        None,
        description="候选的一级科室，用于下一轮对比鉴别"
    )
    
    candidate_secondary_department: Optional[str] = Field(
        None,
        description="候选的二级科室，用于下一轮对比鉴别"
    )
