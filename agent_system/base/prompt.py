class BasePrompt:
    description: str = None
    instructions: str = None
    
    def __init__(self):
        if self.description is None:
            raise NotImplementedError("子类必须定义 'description' 属性")
        if self.instructions is None:
            raise NotImplementedError("子类必须定义 'instructions' 属性")