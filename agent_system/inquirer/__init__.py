"""
Inquirer智能体模块

该模块实现询问者智能体，用于基于患者的现病史和既往史生成医生需要询问的具体问题。
智能体的特殊之处在于其描述和指令主体内容由Prompter智能体动态生成。

主要组件:
- InquirerResponseModel: 询问者智能体的响应数据模型
- InquirerPrompt: 询问者智能体的动态提示词模板
- Inquirer: 询问者智能体的主要实现类
"""

from .response_model import InquirerResponseModel
from .prompt import InquirerPrompt  
from .agent import Inquirer

__all__ = [
    'InquirerResponseModel',
    'InquirerPrompt',
    'Inquirer'
]