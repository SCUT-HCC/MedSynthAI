from typing import List, Dict
from pydantic import BaseModel, Field
from agent_system.base import BaseResponseModel

class EvaluationDimension(BaseModel):
    """单个评价维度"""
    score: float = Field(
        ...,
        description="该维度的评分(0-5分，0分最差，5分最好)",
        ge=0.0,
        le=5.0
    )
    comment: str = Field(
        ..., 
        description="该维度的详细评价和分析"
    )

class EvaluatorResult(BaseResponseModel):
    """评价器评价结果"""
    
    # 基础评价维度（4个）
    clinical_inquiry: EvaluationDimension = Field(
        default=EvaluationDimension(score=0.0, comment="评价失败：临床问诊能力评价缺失"),
        description="临床问诊能力评价"
    )
    communication_quality: EvaluationDimension = Field(
        default=EvaluationDimension(score=0.0, comment="评价失败：沟通表达能力评价缺失"),
        description="沟通表达能力评价"
    )
    information_completeness: EvaluationDimension = Field(
        default=EvaluationDimension(score=0.0, comment="评价失败：信息收集全面性评价缺失"),
        description="信息收集全面性评价"
    )
    overall_professionalism: EvaluationDimension = Field(
        default=EvaluationDimension(score=0.0, comment="评价失败：整体专业性评价缺失"),
        description="整体专业性评价"
    )
    
    # 相似度评价维度（3个）
    present_illness_similarity: EvaluationDimension = Field(
        default=EvaluationDimension(score=0.0, comment="评价失败：现病史相似度评价缺失"),
        description="现病史相似度评价"
    )
    past_history_similarity: EvaluationDimension = Field(
        default=EvaluationDimension(score=0.0, comment="评价失败：既往史相似度评价缺失"),
        description="既往史相似度评价"
    )
    chief_complaint_similarity: EvaluationDimension = Field(
        default=EvaluationDimension(score=0.0, comment="评价失败：主述相似度评价缺失"),
        description="主述相似度评价"
    )

    # 总结和建议
    summary: str = Field(
        default="评价失败：整体评价总结缺失",
        description="整体评价总结"
    )
    key_suggestions: List[str] = Field(
        default=["评价失败：关键改进建议缺失"],
        description="关键改进建议列表"
    )
