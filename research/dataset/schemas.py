from datetime import datetime
from typing import Dict, Optional, List
from pydantic import BaseModel, Field

class MedicalRecord(BaseModel):
    """医疗记录基础模型"""
    record_id: str = Field(..., description="记录ID")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class PatientCase(MedicalRecord):
    """病例数据模型"""
    patient_id: str = Field(..., description="患者ID")
    main_complaint: str = Field(..., description="主诉")
    age: int = Field(..., ge=0, le=150, description="年龄")
    gender: str = Field(..., description="性别")
    present_illness: Dict[str, str] = Field(..., description="现病史")
    past_history: Dict[str, str] = Field(..., description="既往史")
    
class Dataset(BaseModel):
    """数据集元数据模型"""
    name: str = Field(..., description="数据集名称")
    description: str = Field(..., description="数据集描述")
    version: str = Field(..., description="数据集版本")
    created_at: datetime = Field(default_factory=datetime.now)
    cases_count: int = Field(default=0, description="病例数量")
