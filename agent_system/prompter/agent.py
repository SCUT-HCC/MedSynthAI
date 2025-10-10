from typing import Any, List
from agent_system.base import BaseAgent
from agent_system.prompter.prompt import PrompterPrompt
from agent_system.prompter.response_model import PrompterResult


class Prompter(BaseAgent):
    """
    询问智能体生成专家
    
    基于患者的现病史、既往史、主述以及当前具体任务，
    生成针对该任务的专门询问子智能体的description和instructions。
    该子智能体将负责围绕特定主题向患者进行专业的询问。
    
    核心功能:
    1. 理解当前任务的具体要求和询问重点
    2. 整合患者的病史背景信息
    3. 为目标询问子智能体定义清晰的专业角色
    4. 制定仅限于可询问内容的具体指令
    
    Attributes:
        model_type (str): 使用的大语言模型类型，默认为 gpt-oss:latest
        llm_config (dict): LLM模型配置参数
    """
    
    def __init__(self, model_type: str = "gpt-oss:latest", llm_config: dict = None):
        """
        初始化Prompter智能体
        
        Args:
            model_type (str): 大语言模型类型，默认使用 gpt-oss:latest
            llm_config (dict): LLM模型的配置参数，如果为None则使用默认配置
        """
        super().__init__(
            model_type=model_type,
            description="基于患者情况和任务需求生成专门的预问诊询问智能体指导",
            instructions=PrompterPrompt.instructions,
            response_model=PrompterResult,
            llm_config=llm_config or {},
            structured_outputs=True,
            markdown=False,
            use_cache=False
        )
    
    def run(self, hpi_content: str, ph_content: str, chief_complaint: str, current_task: str, specific_guidance: str = "") -> PrompterResult:
        """
        执行预问诊询问智能体生成
        
        基于患者的现病史、既往史、主述、当前具体任务以及Controller提供的询问指导建议，
        生成针对该任务的专门询问子智能体的description和instructions。
        
        Args:
            hpi_content (str): 现病史内容，患者的主要症状描述
            ph_content (str): 既往史内容，患者的历史疾病信息
            chief_complaint (str): 患者主述，患者的主要不适描述
            current_task (str): 当前任务，如"起病情况和患病时间"、"主要症状特征"等
            specific_guidance (str): Controller提供的针对当前任务的询问指导建议，用于优化询问子智能体生成
            
        Returns:
            PrompterResult: 包含询问子智能体描述和指令的结构化数据，包括：
                - description: 为特定询问任务定制的子智能体描述
                - instructions: 为特定询问任务定制的子智能体执行指令列表
                
        Raises:
            Exception: 当LLM调用失败时，返回包含默认信息的PrompterResult
        """
        try:
            # 构建生成提示词
            prompt = self._build_prompt(hpi_content, ph_content, chief_complaint, current_task, specific_guidance)
            
            # 调用基类的run方法执行LLM推理
            result = super().run(prompt)
            
            # 确保返回正确的类型并进行类型转换
            return self._ensure_result_type(result)
            
        except Exception as e:
            # 当生成失败时记录错误并返回默认结果
            print(f"预问诊询问子智能体生成失败: {str(e)}")
            return self._get_fallback_result(current_task)
    
    def _ensure_result_type(self, result: Any) -> PrompterResult:
        """
        确保返回结果为正确的类型
        
        Args:
            result (Any): LLM返回的原始结果
            
        Returns:
            PrompterResult: 转换后的结构化结果
        """
        if isinstance(result, PrompterResult):
            return result
        elif isinstance(result, dict):
            return PrompterResult(**result)
        else:
            # 如果类型不匹配，返回默认结果
            return self._get_fallback_result("未知任务")
    
    def _extract_department_guidance(self, hpi_content: str, chief_complaint: str) -> str:
        """
        根据患者信息提取科室特定的问诊指导
        
        Args:
            hpi_content (str): 现病史内容
            chief_complaint (str): 患者主述
            
        Returns:
            str: 科室特定的问诊指导
        """
        content = f"{chief_complaint} {hpi_content}".lower()
        
        # 妇科关键词检测
        gyn_keywords = ["月经", "怀孕", "妊娠", "妇科", "阴道", "子宫", "卵巢", "经期", "痛经", "闭经", "流产", "避孕", "经期", "月经不规律"]
        if any(keyword in content for keyword in gyn_keywords):
            return """
## 科室特定问诊指导（妇产科）
- **优先级1**: 对于育龄期女性患者，必须首先询问："您最近一次月经是什么时候？"
- **优先级2**: 必须询问月经史："您的月经周期规律吗？每次持续几天？量多还是少？"
- **优先级3**: 必须询问妊娠可能性："有怀孕的可能吗？"
- **优先级4**: 对于异常出血，询问出血量、颜色、持续时间、伴随症状
- **优先级5**: 询问既往妇科病史、手术史、生育史

## 妇产科一级科室判定要点
- **核心问题**: "您的主要不适是什么？"
- **关键区分点**: 
  - 下腹部疼痛：考虑妇科急腹症、盆腔炎、异位妊娠等
  - 阴道异常出血：考虑功能失调性子宫出血、流产、妇科肿瘤等
  - 外阴瘙痒/分泌物异常：考虑阴道炎、宫颈炎等
  - 月经异常：考虑内分泌失调、妇科疾病等
- **必要信息收集**: 末次月经时间、性生活史、避孕措施、生育史

## 妇产科二级科室判定要点
- **妇科方向**: 月经异常、白带异常、下腹痛、外阴瘙痒等
- **产科方向**: 妊娠相关、产检、分娩、产后恢复等
- **计划生育方向**: 避孕咨询、终止妊娠、节育手术等
"""
        
        # 内科关键词检测
        medical_keywords = ["内科", "高血压", "糖尿病", "心脏病", "胸闷", "胸痛", "头晕", "乏力", "发热", "咳嗽", "呼吸困难"]
        if any(keyword in content for keyword in medical_keywords):
            return """
## 科室特定问诊指导（内科）
- **优先级1**: 询问症状持续时间、严重程度、诱发因素
- **优先级2**: 询问既往慢性病史、用药史、家族史
- **优先级3**: 询问生活方式相关因素（饮食、运动、睡眠）
- **优先级4**: 询问相关系统症状（如心血管、呼吸、消化等）

## 内科一级科室判定要点
- **核心问题**: "您的主要不适是什么？"
- **关键区分点**:
  - 心血管症状：胸痛、胸闷、心悸、气短
  - 呼吸系统症状：咳嗽、咳痰、呼吸困难、胸痛
  - 消化系统症状：腹痛、腹泻、恶心、呕吐、食欲不振
  - 神经系统症状：头痛、头晕、意识障碍、肢体无力
- **必要信息收集**: 既往病史、用药史、家族史、生活习惯

## 内科二级科室判定要点
- **心血管内科**: 胸痛、心悸、高血压、冠心病等
- **呼吸内科**: 咳嗽、哮喘、肺炎、慢阻肺等
- **消化内科**: 腹痛、胃炎、肝炎、消化道出血等
- **神经内科**: 头痛、眩晕、脑血管疾病、癫痫等
- **内分泌科**: 糖尿病、甲状腺疾病、肥胖等
"""
        
        # 外科关键词检测
        surgery_keywords = ["外科", "外伤", "手术", "肿块", "疼痛", "骨折", "扭伤", "出血", "创伤", "肿瘤"]
        if any(keyword in content for keyword in surgery_keywords):
            return """
## 科室特定问诊指导（外科）
- **优先级1**: 询问外伤史："有无相关的外伤、撞击或扭伤经历？"
- **优先级2**: 询问症状出现时间、发展过程、加重缓解因素
- **优先级3**: 询问既往手术史、外伤史、过敏史
- **优先级4**: 询问相关功能受限情况

## 外科一级科室判定要点
- **核心问题**: "您的主要不适是什么？"
- **关键区分点**:
  - 急性外伤：开放性伤口、骨折、脱位、软组织损伤
  - 慢性病变：肿块、疼痛、功能障碍、畸形
  - 感染性疾病：红肿热痛、化脓、发热
  - 肿瘤性疾病：无痛性肿块、进行性增大、压迫症状
- **必要信息收集**: 外伤史、手术史、过敏史、功能受限情况

## 外科二级科室判定要点
- **普外科**: 腹部疾病、肝胆疾病、胃肠疾病、疝气等
- **骨科**: 骨折、关节脱位、脊柱疾病、运动损伤等
- **泌尿外科**: 泌尿系结石、前列腺疾病、泌尿系肿瘤等
- **胸外科**: 胸部外伤、肺部肿瘤、食管疾病等
- **神经外科**: 颅脑外伤、脑肿瘤、脊髓疾病等
"""
        
        # 儿科关键词检测
        pediatric_keywords = ["儿童", "小孩", "婴儿", "幼儿", "发烧", "咳嗽", "拉肚子", "不吃奶", "哭闹", "发育"]
        if any(keyword in content for keyword in pediatric_keywords):
            return """
## 科室特定问诊指导（儿科）
- **优先级1**: 询问患儿年龄、体重、发育情况
- **优先级2**: 询问疫苗接种史、既往疾病史
- **优先级3**: 询问喂养/饮食情况、睡眠状况
- **优先级4**: 询问生长发育里程碑达成情况
- **优先级5**: 询问家族遗传病史

## 儿科一级科室判定要点
- **核心问题**: "孩子主要有什么问题？"
- **关键区分点**:
  - 新生儿期（0-28天）：黄疸、喂养困难、呼吸困难
  - 婴儿期（28天-1岁）：发热、腹泻、咳嗽、发育迟缓
  - 幼儿期（1-3岁）：发热、咳嗽、腹泻、外伤
  - 学龄前期（3-6岁）：发热、咳嗽、腹痛、传染病
- **必要信息收集**: 出生史、疫苗接种史、生长发育史、喂养史

## 儿科二级科室判定要点
- **儿内科**: 呼吸系统、消化系统、神经系统疾病等
- **新生儿科**: 新生儿黄疸、新生儿肺炎、早产儿等
- **儿外科**: 先天性畸形、急腹症、外伤等
- **儿童保健科**: 生长发育评估、营养指导、预防接种等
"""
        
        # 眼科关键词检测
        eye_keywords = ["眼睛", "视力", "看不清", "眼痛", "眼红", "流泪", "白内障", "青光眼"]
        if any(keyword in content for keyword in eye_keywords):
            return """
## 科室特定问诊指导（眼科）
- **优先级1**: 询问视力变化情况、持续时间
- **优先级2**: 询问眼部症状：疼痛、红肿、分泌物、流泪等
- **优先级3**: 询问既往眼科病史、手术史、外伤史
- **优先级4**: 询问全身疾病史（糖尿病、高血压等）
- **优先级5**: 询问家族眼科疾病史

## 眼科一级科室判定要点
- **核心问题**: "您的眼部主要有什么不适？"
- **关键区分点**:
  - 视力问题：近视、远视、散光、老花、白内障
  - 眼部症状：眼痛、眼红、流泪、畏光、异物感
  - 眼部外伤：机械性损伤、化学性损伤、热烧伤
  - 眼部疾病：青光眼、白内障、视网膜疾病、眼表疾病
- **必要信息收集**: 视力变化史、眼部症状史、既往眼科病史

## 眼科二级科室判定要点
- **白内障科**: 老年性白内障、先天性白内障、外伤性白内障
- **青光眼科**: 原发性青光眼、继发性青光眼、先天性青光眼
- **视网膜科**: 视网膜脱离、糖尿病视网膜病变、黄斑病变
- **眼整形科**: 眼睑疾病、泪道疾病、眼眶疾病等
"""
        
        return ""

    def _get_fallback_result(self, task_name: str) -> PrompterResult:
        """
        生成失败时的默认结果
        
        Args:
            task_name (str): 任务名称
            
        Returns:
            PrompterResult: 包含默认内容的结果
        """
        return PrompterResult(
            description=f"你是一名专业的预问诊询问医生，负责针对'{task_name}'进行详细的询问信息收集。你需要以专业、耐心的态度与患者交流，通过询问获取准确完整的相关信息。",
            instructions=[
                "## 询问重点",
                f"1. 围绕'{task_name}'主题进行系统性询问",
                "2. 使用通俗易懂的语言与患者交流",
                "3. 确保询问信息的准确性和完整性",
                "",
                "## 注意事项",
                "- 保持专业和耐心的态度",
                "- 避免使用过于复杂的医学术语",
                "- 仅通过询问获取信息，不进行任何检查或检验",
                "- 引导患者提供具体详细的信息"
            ]
        )
    
    def _build_prompt(self, hpi_content: str, ph_content: str, chief_complaint: str, current_task: str, specific_guidance: str = "") -> str:
        """
        构建Prompter的提示词模板
        
        根据患者病史信息、当前任务和Controller的具体指导建议，构建用于生成子智能体的提示词。
        
        Args:
            hpi_content (str): 现病史内容
            ph_content (str): 既往史内容
            chief_complaint (str): 患者主述
            current_task (str): 当前任务
            specific_guidance (str): Controller提供的具体指导建议
            
        Returns:
            str: 构建的提示词
        """
        # 确保既往史内容的合理显示
        past_history_display = ph_content.strip() if ph_content.strip() else "暂无既往史信息"
        
        # 处理具体指导建议
        guidance_section = ""
        if specific_guidance.strip():
            guidance_section = f"""
Controller指导建议: {specific_guidance}
"""
        
        # 从prompt类获取科室特定指导
        from agent_system.prompter.prompt import PrompterPrompt
        example_output = PrompterPrompt.get_example_output()
        
        # 提取科室特定问诊指导 - 仅在一级或二级科室判定时调用
        department_guidance = ""
        if current_task == "一级科室判定" or current_task == "二级科室判定":
            department_guidance = self._extract_department_guidance(hpi_content, chief_complaint)
        
        prompt = f"""患者基本信息：
患者主诉: {chief_complaint}
现病史: {hpi_content}
既往史: {past_history_display}

当前任务: {current_task}{guidance_section}

{department_guidance}

已知信息提醒：以上是患者已经提供的基本信息，请在生成询问策略时避免重复询问这些内容。

请按照以下步骤生成一个专门的预问诊询问子智能体，该智能体将负责围绕"{current_task}"主题向患者进行专业询问：

## 步骤1: 分析任务特点
- 深入理解"{current_task}"的核心要求和关键询问点
- 结合患者的现病史和主诉，识别与该任务相关的重要信息
- 如果有Controller指导建议，重点考虑其中的专业建议和注意事项
- **重要**：避免询问患者已经明确提供的信息（如主诉、现病史、既往史中已有的内容）

## 步骤2: 设计智能体角色
- 为子智能体定义专业的医疗角色和身份
- 明确该智能体在"{current_task}"方面的专业能力和职责范围
- 确保角色设计与患者的具体病情背景相匹配

## 步骤3: 制定询问策略
- 基于任务特点和患者信息，设计系统性的询问流程
- 将复杂的医疗询问分解为患者易于理解和回答的具体问题
- 优先询问科室特定的关键信息（如妇科的月经史、妊娠可能等）
- 确保询问内容全面、有序、针对性强
- **重要**：专注于询问缺失或需要进一步了解的信息，避免重复已知内容

## 步骤4: 完善执行指令
- 详细说明子智能体应如何执行询问任务
- 包含具体的询问技巧、注意事项和质量要求
- 确保指令具有可操作性和实用性
- **重要**：在指令中明确要求子智能体检查患者已提供的信息，避免重复询问

请为该子智能体提供：
1. description - 描述该智能体的角色、专业领域和主要职责
2. instructions - 详细的执行指令列表，包括询问步骤、注意事项等

输出格式示例：
{example_output}

请严格按照上述JSON格式输出。
输出内容为:"""
        
        return prompt