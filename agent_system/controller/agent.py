from typing import Dict, Any, List
from agent_system.base import BaseAgent
from agent_system.controller.prompt import ControllerPrompt
from agent_system.controller.response_model import ControllerDecision


class TaskController(BaseAgent):
    """
    任务控制器智能体
    
    负责根据患者的临床信息（现病史、既往史、主诉）从未完成的任务列表中
    选择最合适的下一步任务，并提供预问诊询问指导建议。
    
    核心功能:
    1. 分析患者的临床信息和病情特征
    2. 选择最重要的询问任务
    3. 提供针对性的预问诊询问指导
    4. 确保指导内容仅限于医生可询问的信息
    
    Attributes:
        model_type (str): 使用的大语言模型类型，默认为 gpt-oss:latest
        llm_config (dict): LLM模型配置参数
        simple_mode (bool): 简化模式标志，True时自动选择第一个任务并返回固定指导
    """
    
    def __init__(self, model_type: str = "gpt-oss:latest", llm_config: dict = None, 
                 simple_mode: bool = False, score_driven_mode: bool = False):
        """
        初始化任务控制器智能体
        
        Args:
            model_type (str): 大语言模型类型，默认使用 gpt-oss:latest
            llm_config (dict): LLM模型的配置参数，如果为None则使用默认配置
            simple_mode (bool): 简化模式，如果为True则自动选择第一个任务并返回固定指导，默认为False
            score_driven_mode (bool): 分数驱动模式，如果为True则选择当前任务组中分数最低的任务，默认为False
        
        Note:
            score_driven_mode和simple_mode不能同时为True，如果同时为True则优先使用score_driven_mode
        """
        self.simple_mode = simple_mode
        self.score_driven_mode = score_driven_mode
        super().__init__(
            model_type=model_type,
            description="医疗任务控制器，负责任务选择和预问诊询问指导",
            instructions=ControllerPrompt.instructions,
            response_model=ControllerDecision,
            llm_config=llm_config or {},
            structured_outputs=True,
            markdown=False,
            use_cache=False
        )
    
    def run(self, 
            pending_tasks: List[Dict[str, str]], 
            chief_complaint: str, 
            hpi_content: str = "", 
            ph_content: str = "",
            additional_info: str = "",
            task_manager = None) -> ControllerDecision:
        """
        执行任务控制决策
        
        基于患者的临床信息和待执行的任务列表，选择最合适的任务
        并提供具体的执行指导建议。
        
        Args:
            pending_tasks (List[Dict[str, str]]): 待执行的任务列表，每个任务包含name、description字段
            chief_complaint (str): 患者主诉
            hpi_content (str, optional): 现病史内容，默认为空字符串
            ph_content (str, optional): 既往史内容，默认为空字符串
            additional_info (str, optional): 附加信息，可能包含补充的临床信息，默认为空字符串
            
        Returns:
            ControllerDecision: 包含任务选择决策和预问诊询问指导的结构化数据，包括：
                - selected_task: 选择的任务名称
                - specific_guidance: 针对选定任务的预问诊询问指导建议
                
        Raises:
            Exception: 当LLM调用失败时，返回包含默认信息的ControllerDecision
        """
        try:
            # 分数驱动模式：选择当前任务组中分数最低的任务
            if self.score_driven_mode and task_manager is not None:
                return self._get_score_driven_result(pending_tasks, task_manager)
            
            # 简化模式：直接选择第一个任务并返回固定指导
            elif self.simple_mode:
                return self._get_simple_mode_result(pending_tasks)
            
            # 构建决策提示词
            prompt = self._build_decision_prompt(
                pending_tasks, chief_complaint, hpi_content, ph_content, additional_info
            )
            
            # 调用基类的run方法执行LLM推理
            result = super().run(prompt)
            
            # 确保返回正确的类型并进行类型转换
            return self._ensure_result_type(result)
            
        except Exception as e:
            # 当决策失败时记录错误并返回默认结果
            print(f"任务控制决策失败: {str(e)}")
            return self._get_fallback_result(pending_tasks)
    
    def _ensure_result_type(self, result: Any) -> ControllerDecision:
        """
        确保返回结果为正确的类型
        
        Args:
            result (Any): LLM返回的原始结果
            
        Returns:
            ControllerDecision: 转换后的结构化结果
        """
        if isinstance(result, ControllerDecision):
            return result
        elif isinstance(result, dict):
            return ControllerDecision(**result)
        else:
            # 如果类型不匹配，返回默认结果
            return self._get_fallback_result([])
    
    def _get_score_driven_result(self, pending_tasks: List[Dict[str, str]], task_manager) -> ControllerDecision:
        """
        分数驱动模式下生成决策结果
        
        在分数驱动模式下，从当前任务组的未完成任务中选择分数最低的任务，
        并返回相应的询问指导。这是基于数值比较的算法选择，无需LLM参与。
        
        Args:
            pending_tasks (List[Dict[str, str]]): 待执行的任务列表，包含name和description
            task_manager: 任务管理器实例，用于获取任务分数信息
            
        Returns:
            ControllerDecision: 包含分数驱动模式任务选择和指导的结果
        """
        if not pending_tasks:
            return ControllerDecision(
                selected_task="基本信息收集",
                specific_guidance="当前没有待执行任务，请按照标准医疗询问流程进行患者评估。"
            )
        
        # 获取当前任务阶段
        current_phase = task_manager.get_current_phase()
        
        # 获取当前阶段的任务分数
        phase_scores = task_manager.get_task_scores(current_phase)
        
        # 在待执行任务中找到分数最低的任务
        lowest_score_task = None
        lowest_score = float('inf')
        
        for task in pending_tasks:
            task_name = task.get("name", "")
            task_score = phase_scores.get(task_name, 0.0)
            
            if task_score < lowest_score:
                lowest_score = task_score
                lowest_score_task = task
        
        # 如果没有找到合适的任务，选择第一个并记录错误日志
        if lowest_score_task is None:
            # 使用logger记录错误，如果没有logger则使用print作为后备
            error_msg = f"Controller-ScoreDriven警告：在阶段{current_phase.value}中未找到合适任务，使用默认第一个任务"
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(error_msg)
            except:
                print(f"[ERROR] {error_msg}")
            
            lowest_score_task = pending_tasks[0]
            lowest_score = phase_scores.get(lowest_score_task.get("name", ""), 0.0)
        
        selected_task_name = lowest_score_task.get("name", "未知任务")
        
        # 使用和simple模式相同的固定指导
        return ControllerDecision(
            selected_task=selected_task_name,
            specific_guidance="请按照标准医疗询问流程进行患者评估，基于患者临床信息选择最重要的询问任务，提供针对性的、具体的、可操作的询问指导建议，确保指导内容仅限于医生可以通过询问获取的信息。"
        )
    
    def _get_simple_mode_result(self, pending_tasks: List[Dict[str, str]]) -> ControllerDecision:
        """
        简化模式下生成决策结果
        
        在简化模式下，直接选择第一个待执行任务，并返回固定的询问指导。
        
        Args:
            pending_tasks (List[Dict[str, str]]): 待执行的任务列表
            
        Returns:
            ControllerDecision: 包含简化模式任务选择和固定指导的结果
        """
        # 如果有待执行任务，选择第一个作为默认任务
        if pending_tasks:
            selected_task = pending_tasks[0]
            selected_task_name = selected_task.get("name", "未知任务")
        else:
            selected_task_name = "基本信息收集"
        
        return ControllerDecision(
            selected_task=selected_task_name,
            specific_guidance="请按照标准医疗询问流程进行患者评估，基于患者临床信息选择最重要的询问任务，提供针对性的、具体的、可操作的询问指导建议，确保指导内容仅限于医生可以通过询问获取的信息。"
        )
    
    def _get_fallback_result(self, pending_tasks: List[Dict[str, str]]) -> ControllerDecision:
        """
        生成决策失败时的默认结果
        
        Args:
            pending_tasks (List[Dict[str, str]]): 待执行的任务列表
            
        Returns:
            ControllerDecision: 包含默认任务选择的结果
        """
        # 如果有待执行任务，选择第一个作为默认任务
        if pending_tasks:
            default_task = pending_tasks[0]
            selected_task_name = default_task.get("name", "未知任务")
        else:
            selected_task_name = "基本信息收集"
        
        return ControllerDecision(
            selected_task=selected_task_name,
            specific_guidance="由于系统异常，请按照标准临床询问流程进行患者评估，重点询问患者的主要症状、起病过程和伴随症状等基本病史信息。"
        )
    
    def _build_decision_prompt(self, 
                              pending_tasks: List[Dict[str, str]], 
                              chief_complaint: str, 
                              hpi_content: str, 
                              ph_content: str,
                              additional_info: str = "") -> str:
        """
        构建任务控制决策的提示词模板
        
        根据待执行任务列表和患者临床信息，构建简洁高效的决策提示词，
        引导LLM进行专业的任务选择和指导建议。
        
        Args:
            pending_tasks (List[Dict[str, str]]): 待执行的任务列表
            chief_complaint (str): 患者主诉
            hpi_content (str): 现病史内容
            ph_content (str): 既往史内容
            additional_info (str, optional): 附加信息，默认为空字符串
            
        Returns:
            str: 精简的决策提示词
        """
        # 格式化待执行任务列表
        tasks_display = ""
        for i, task in enumerate(pending_tasks, 1):
            task_name = task.get("name", "未知任务")
            task_desc = task.get("description", "无描述")
            tasks_display += f"{i}. 任务名称: {task_name}\n   描述: {task_desc}\n\n"
        
        if not tasks_display.strip():
            tasks_display = "当前没有待执行的任务。"
        
        # 确保临床信息的合理显示
        hpi_display = hpi_content.strip() if hpi_content.strip() else "暂无现病史信息"
        ph_display = ph_content.strip() if ph_content.strip() else "暂无既往史信息"
        
        # 处理附加信息
        additional_info_section = ""
        if additional_info.strip():
            additional_info_section = f"\n附加信息: {additional_info.strip()}"
        
        # 检查是否包含科室判定任务，并生成特殊指导
        department_guidance = self._generate_department_guidance(pending_tasks, additional_info)
        
        # 从prompt类获取示例输出格式
        example_output = ControllerPrompt.get_example_output()
        
        prompt = f"""患者临床信息：
主诉: {chief_complaint}
现病史: {hpi_display}
既往史: {ph_display}{additional_info_section}

待执行任务列表：
{tasks_display}

请根据患者的临床信息分析病情特征，从上述任务列表中选择最合适的下一步任务，并提供具体的执行指导建议。

{department_guidance}

输出格式示例：
{example_output}

请严格按照上述JSON格式输出。
输出内容为:"""
        
        return prompt
    
    def _generate_department_guidance(self, pending_tasks: List[Dict[str, str]], additional_info: str) -> str:
        """
        为科室判定任务生成特殊指导
        
        当任务列表中包含科室判定相关任务时，利用附加信息（医院科室信息和上一轮分诊结果）
        生成针对科室分诊的特殊指导，重点关注容易混淆的科室和误判风险。
        
        Args:
            pending_tasks (List[Dict[str, str]]): 待执行的任务列表
            additional_info (str): 分诊附加信息，包含医院科室信息和上一轮分诊结果
            
        Returns:
            str: 科室判定的特殊指导内容，如果没有相关任务则返回空字符串
        """
        # 检查是否有科室判定相关的任务
        department_tasks = []
        for task in pending_tasks:
            task_name = task.get("name", "").lower()
            if any(keyword in task_name for keyword in ["科室", "分诊", "department"]):
                department_tasks.append(task)
        
        if not department_tasks or not additional_info.strip():
            return ""
        
        # 生成科室判定的特殊指导
        guidance_parts = ["## 科室判定任务特别指导"]
        guidance_parts.append(
            "如果选择科室判定任务，请在询问时重点关注："
        )
        
        for task in department_tasks:
            task_name = task.get("name", "")
            if "一级科室" in task_name:
                guidance_parts.extend([
                    "- 详细询问患者症状特征，结合医院科室设置判断最适合的一级科室",
                    "- 询问症状的具体表现，与其他一级科室易混淆症状进行鉴别",
                    "- 通过询问病史和症状发展过程，排除其他可能的科室选择",
                    "- 重点询问与科室判定相关的关键症状和体征"
                ])
            elif "二级科室" in task_name:
                guidance_parts.extend([
                    "- 基于一级科室判定结果，询问更详细的专业相关症状",
                    "- 通过询问了解患者症状的专业特征，区分二级科室内不同专业方向",
                    "- 询问既往相关疾病史和家族史，辅助二级科室判定",
                    "- 重点询问能帮助细分专业科室的特异性症状"
                ])
        
        # 将附加信息内容整合到指导中
        if additional_info.strip():
            guidance_parts.append("\n## 医院具体情况参考：")
            guidance_parts.extend(additional_info.splitlines())

        return "\n".join(guidance_parts)
    
    def select_optimal_task(self, 
                           tasks: List[Dict[str, str]], 
                           patient_info: Dict[str, str]) -> ControllerDecision:
        """
        基于患者信息选择最优任务的便捷接口
        
        这是一个专门用于任务选择的简化接口，接受结构化的患者信息。
        
        Args:
            tasks (List[Dict[str, str]]): 待执行的任务列表
            patient_info (Dict[str, str]): 患者信息字典，包含chief_complaint、hpi、ph、additional_info等字段
            
        Returns:
            ControllerDecision: 任务选择决策结果
        """
        chief_complaint = patient_info.get("chief_complaint", "")
        hpi_content = patient_info.get("hpi", "")
        ph_content = patient_info.get("ph", "")
        additional_info = patient_info.get("additional_info", "")
        
        return self.run(
            pending_tasks=tasks,
            chief_complaint=chief_complaint,
            hpi_content=hpi_content,
            ph_content=ph_content,
            additional_info=additional_info
        )
    
    def get_task_guidance(self, result: ControllerDecision) -> Dict[str, Any]:
        """
        获取任务指导的结构化信息
        
        Args:
            result (ControllerDecision): 控制器决策结果
            
        Returns:
            Dict[str, Any]: 包含任务指导信息的字典
        """
        return {
            "task_name": result.selected_task,
            "guidance": result.specific_guidance
        }