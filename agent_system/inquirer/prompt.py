from agent_system.base import BasePrompt


class InquirerPrompt(BasePrompt):
    """
    询问者智能体的提示词模板
    
    该提示词模板的description和instructions主体内容由Prompter智能体动态生成，
    只在末尾添加固定的输入信息和输出格式要求。
    """
    
    # 基础描述，将被prompter结果动态替换
    description = ""
    
    # 基础指令，将被prompter结果动态替换
    instructions = []
    
    @staticmethod
    def get_example_output() -> str:
        """
        获取示例输出格式，用于指导 LLM 生成符合要求的结构化输出
        
        Returns:
            str: JSON 格式的示例输出
        """
        return """{
  "current_chat": "请问头痛什么时候开始的？疼痛程度如何？"
}"""
    
    @staticmethod
    def get_fixed_format_instructions() -> list:
        """
        获取固定的输入输出格式指令
        
        Returns:
            list: 固定的格式指令列表
        """
        return [
            "",
            "## 患者信息输入格式",
            "- 现病史: 患者当前疾病的详细描述",
            "- 既往史: 患者过往的疾病史和治疗史",
            "",
            "## 输出要求",
            "生成的问诊问题应该:",
            "1. 可以问2-3个相关问题，但总长度不超过80字",
            "2. 问题必须简洁明了，符合真实医患对话习惯",
            "3. 优先询问最紧急、最重要的症状信息",
            "4. 使用患者容易理解的日常用语",
            "5. 避免冗长的分点罗列，用自然对话方式提问",
            "6. 问题要具有针对性，直接关联患者主诉",
            "",
            "## 示例输出格式（JSON）",
            InquirerPrompt.get_example_output()
        ]