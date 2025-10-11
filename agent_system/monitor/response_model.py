from pydantic import Field
from agent_system.base import BaseResponseModel

class MonitorResult(BaseResponseModel):
    """
    Monitor监控结果模型
    """
    completion_score: float = Field(
        ...,
        description="完成度评分（0.0-1.0）",
        ge=0.0,
        le=1.0
    )
    reason: str = Field(
        ...,
        description="评分理由，详细说明为什么给出这个评分"
    )