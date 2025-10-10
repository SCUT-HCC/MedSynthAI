from pydantic import Field
from agent_system.base import BaseResponseModel


class ControllerDecision(BaseResponseModel):
    """
    Controller智能体决策结果模型
    
    基于未完成的任务列表、现病史、既往史与主诉，
    输出选择的任务以及具体的预问诊询问指导建议。
    """
    
    selected_task: str = Field(
        ...,
        description="选择执行的任务名称"
    )
    
    specific_guidance: str = Field(
        ...,
        description="针对选定任务的预问诊询问指导建议，仅包含医生可以通过询问获取的信息，不包含任何需要设备检查、化验、检验等内容"
    )