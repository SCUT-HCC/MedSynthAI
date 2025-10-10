from typing import List
from pydantic import Field
from agent_system.base import BaseResponseModel

class PrompterResult(BaseResponseModel):
    """
    Prompter智能体分析结果模型
    
    用于输出为特定任务定制的子智能体的描述和指令内容
    """
    description: str = Field(
        ...,
        description="为特定任务定制的子智能体描述，说明该智能体的角色、任务和目标"
    )
    instructions: List[str] = Field(
        default_factory=list,
        description="为特定任务定制的子智能体执行指令列表，包含具体的执行步骤和注意事项"
    )