from agent_system.base import BaseAgent
from agent_system.inquirer.prompt import InquirerPrompt
from agent_system.inquirer.response_model import InquirerResponseModel


class Inquirer(BaseAgent):
    """
    询问者智能体
    
    基于患者的现病史和既往史，生成医生需要询问的具体问题。
    该智能体的特殊之处在于其描述和指令主体内容由Prompter智能体动态生成，
    然后结合固定的输入输出格式构成完整的提示词。
    
    核心功能:
    1. 接收患者的现病史和既往史信息
    2. 基于Prompter生成的询问策略产生具体的问诊问题
    3. 输出符合医患交流习惯的问题内容
    
    Attributes:
        model_type (str): 使用的大语言模型类型，默认为 gpt-oss:latest
        llm_config (dict): LLM模型配置参数
    """
    
    def __init__(self, description: str, instructions: list, model_type: str = "gpt-oss:latest", llm_config: dict = None):
        """
        初始化Inquirer智能体
        
        Args:
            description (str): 由Prompter生成的智能体描述
            instructions (list): 由Prompter生成的指令列表
            model_type (str): 大语言模型类型，默认使用 gpt-oss:latest
            llm_config (dict): LLM模型的配置参数，如果为None则使用默认配置
        """
        # 将Prompter生成的指令与固定格式指令拼接
        complete_instructions = instructions.copy()
        complete_instructions.extend(InquirerPrompt.get_fixed_format_instructions())
        
        super().__init__(
            model_type=model_type,
            description=description,
            instructions=complete_instructions,
            response_model=InquirerResponseModel,
            llm_config=llm_config or {},
            structured_outputs=True,
            markdown=False,
            use_cache=False
        )
    
    def run(self, hpi_content: str, ph_content: str, chief_complaint: str) -> InquirerResponseModel:
        """
        执行询问者智能体的问题生成
        
        基于患者病史信息生成具体的问诊问题。
        
        Args:
            hpi_content (str): 现病史内容，患者的主要症状描述
            ph_content (str): 既往史内容，患者的历史疾病信息
            chief_complaint (str): 患者主述，患者的主要不适描述
            
        Returns:
            InquirerResponseModel: 包含生成的问诊问题的结构化数据：
                - current_chat: 生成的具体问诊问题内容
        """
        # 构建询问提示词
        prompt = self._build_prompt(hpi_content, ph_content, chief_complaint)
        
        # 调用基类的run方法执行LLM推理
        result = super().run(prompt)
        
        return result
    
    def _build_prompt(self, hpi_content: str, ph_content: str, chief_complaint: str) -> str:
        """
        构建Inquirer的提示词模板
        
        将患者的病史信息构建完整的提示词。
        
        Args:
            hpi_content (str): 现病史内容
            ph_content (str): 既往史内容
            chief_complaint (str): 患者主述
            
        Returns:
            str: 构建的提示词
        """
        # 确保既往史内容的合理显示
        past_history_display = ph_content.strip() if ph_content.strip() else "暂无既往史信息"
        
        # 获取示例输出格式
        example_output = InquirerPrompt.get_example_output()
        
        prompt = f"""患者基本信息：
患者主诉: {chief_complaint}
现病史: {hpi_content}
既往史: {past_history_display}

已知信息提醒：以上是患者已经提供的基本信息，请在生成问诊问题时避免重复询问这些内容，专注于询问缺失或需要进一步了解的信息。

基于以上患者信息，请生成简洁的问诊问题。

重要提醒：
- 可以问2-3个相关问题，但总长度控制在80字以内
- 用自然对话方式提问，避免分点罗列
- 问题要简短精悍，符合真实问诊场景
- **重要**：避免询问患者已经明确提供的信息（如主诉、现病史、既往史中已有的内容）
- **重要**：专注于询问缺失或需要进一步了解的信息，避免重复已知内容

输出格式示例：
{example_output}

请严格按照上述JSON格式输出。
输出内容为:"""
        
        return prompt