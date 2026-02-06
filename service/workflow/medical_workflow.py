from typing import Dict, Any, Optional
import time
from .task_manager import TaskManager, TaskPhase
from .step_executor import StepExecutor
from .workflow_logger import WorkflowLogger

class MedicalWorkflow:
    """
    医疗问诊工作流主控制器
    负责协调整个30步问诊过程的执行
    """
    
    def __init__(self,  model_type: str = "deepseek", 
                 llm_config: Optional[Dict] = None, max_steps: int = 30, log_dir: str = "logs",
                 controller_mode: str = "normal",
                 guidance_loader: Optional[Any] = None,department_guidance: str = "",):
        """
        初始化医疗问诊工作流
        
        Args:
            model_type: 使用的语言模型类型，默认为"gpt-oss:latest"
            llm_config: 语言模型配置，默认为None
            max_steps: 最大执行步数，默认为30
            log_dir: 日志目录，默认为"logs"
            controller_mode: 任务控制器模式，'normal'为智能模式，'sequence'为顺序模式，'score_driven'为分数驱动模式
            guidance_loader: GuidanceLoader实例，用于加载动态指导内容
            department_guidance: 科室指导内容，默认为空字符串(如果在初始化时传入了固定的科室指导（例如通过 --department_filter 参数指定），current_guidance 会被设置为该固定指导内容。如果没有传入固定指导，current_guidance 初始值为空字符串 "")
        """
        self.model_type = model_type
        self.llm_config = llm_config or {}
        self.max_steps = max_steps
        
        # 初始化核心组件
        self.task_manager = TaskManager()
        self.step_executor = StepExecutor(
            model_type=model_type, 
            llm_config=self.llm_config, 
            controller_mode=controller_mode,
            guidance_loader=guidance_loader,  # 将 GuidanceLoader 传递给 StepExecutor
        )
        
        # 重置历史评分，确保新的工作流从零开始
        StepExecutor.reset_historical_scores() #StepExecutor单步执行器
        
        # 初始化工作流状态
        self.current_step = 0
        self.conversation_history = ""   # 完整对话历史
        self.current_hpi = ""
        self.current_ph = ""
        self.current_chief_complaint = ""
        self.current_triage = {
            "primary_department": "",
            "secondary_department": "",
            "triage_reasoning": "",
            "candidate_primary_department": "",
            "candidate_secondary_department": "",

        }
        self.workflow_completed = False
        self.workflow_success = False
        self.current_guidance = department_guidance
    def run(self) -> str:
        try:
            # 执行工作流的主循环
            for step in range(1, self.max_steps + 1):
                self.current_step = step
                
                # 检查是否所有任务都已完成
                if self.task_manager.is_workflow_completed():
                    print(f"所有任务已完成，工作流在第 {step} 步结束")
                    self.workflow_completed = True
                    self.workflow_success = True
                    break
                
                # 执行单个step
                if not self._execute_single_step(step):
                    print(f"Step {step} 执行失败，工作流终止")
                    break
                
                # 打印step进度信息
                self._print_step_progress(step)
            
            # 如果达到最大步数但任务未完成
            if not self.workflow_completed:
                print(f"已达到最大步数 {self.max_steps}，工作流结束")
                self.workflow_success = False
            
        except Exception as e:
            print(f"工作流执行出现异常: {str(e)}")
            self.logger.log_error(self.current_step, "workflow_error", str(e))
            self.workflow_success = False
        
        finally:
            # 记录工作流完成信息
            final_summary = self.task_manager.get_completion_summary()
            self.logger.log_workflow_complete(
                total_steps=self.current_step,
                final_summary=final_summary,
                success=self.workflow_success
            )
        
        print(f"工作流执行完成，日志文件：{self.logger.get_log_file_path()}")
        return self.logger.get_log_file_path()
    
    def _execute_single_step(self, step_num: int) -> bool:
        """
        执行单个step
        
        Args:
            step_num: step编号
            
        Returns:
            bool: 是否执行成功
        """
        try:
            # 更新TaskManager中的当前步骤
            self.task_manager.update_step(step_num)
            
            # 获取当前阶段和待完成任务
            current_phase = self.task_manager.get_current_phase()
            pending_tasks = self.task_manager.get_pending_tasks(current_phase)
            
            # 记录step开始
            self.logger.log_step_start(step_num, current_phase.value, pending_tasks)
            
            # 确定是否为第一步
            is_first_step = (step_num == 1)
            
            # 准备医生问题（非首轮时使用上轮的结果）
            doctor_question = getattr(self, '_last_doctor_question', "")
            
            # 执行step
            step_result = self.step_executor.execute_step(
                step_num=step_num,
                case_data=self.case_data,
                task_manager=self.task_manager,
                logger=self.logger,
                conversation_history=self.conversation_history,
                previous_hpi=self.current_hpi,
                previous_ph=self.current_ph,
                previous_chief_complaint=self.current_chief_complaint,
                previous_department=f"{self.current_triage.get('primary_department', '')}-{self.current_triage.get('secondary_department', '')}",
                previous_candidate_department=f"{self.current_triage.get('candidate_primary_department', '')}-{self.current_triage.get('candidate_secondary_department', '')}",
                previous_triage_reasoning=self.current_triage.get("triage_reasoning", ""),
                current_guidance=self.current_guidance,
                is_first_step=is_first_step,
                doctor_question=doctor_question,
            )
            
            # 检查执行结果
            if not step_result["success"]:
                print(f"Step {step_num} 执行失败: {step_result.get('errors', [])}")
                return False
            
            # 更新工作流状态
            self._update_workflow_state(step_result)
            
            # 记录step完成
            self.logger.log_step_complete(
                step_num=step_num,
                doctor_question=step_result["doctor_question"],
                conversation_history=step_result["conversation_history"],
                task_completion_summary=step_result["task_completion_summary"]
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Step {step_num} 执行异常: {str(e)}"
            print(error_msg)
            self.logger.log_error(step_num, "step_error", error_msg)
            return False
    
    def _update_workflow_state(self, step_result: Dict[str, Any]):
        """
        根据step执行结果更新工作流状态
        
        Args:
            step_result: step执行结果
        """
        self.conversation_history = step_result["conversation_history"]
        self.current_hpi = step_result["updated_hpi"]
        self.current_ph = step_result["updated_ph"]
        self.current_chief_complaint = step_result["updated_chief_complaint"]
        self.current_triage = step_result["triage_result"]
        self._last_doctor_question = step_result["doctor_question"]
        self.current_guidance = step_result.get("new_guidance", self.current_guidance)
    def _print_step_progress(self, step_num: int):
        """
        打印step进度信息
        
        Args:
            step_num: step编号
        """
        current_phase = self.task_manager.get_current_phase()
        completion_summary = self.task_manager.get_completion_summary()
        
        print(f"\n=== Step {step_num} 完成 ===")
        print(f"当前阶段: {current_phase.value}")
        
        # 显示分诊信息
        if self.current_triage and self.current_triage.get("primary_department") and self.current_triage.get("candidate_secondary_department"):
            print(f"科室分诊: {self.current_triage['primary_department']} → {self.current_triage['secondary_department']}")
            print(f"候选科室分诊: {self.current_triage['candidate_primary_department']} → {self.current_triage['candidate_secondary_department']}")
            print(f"分诊理由: {self.current_triage['triage_reasoning'][:50]}...")
        
        # 显示各阶段完成情况
        for phase_name, phase_info in completion_summary["phases"].items():
            status = "✓" if phase_info["is_completed"] else "○"
            print(f"{status} {phase_name}: {phase_info['completed']}/{phase_info['total']} 任务完成 "
                  f"({phase_info['completion_rate']:.1%})")
        
        print(f"对话轮次: {step_num}")
        print(f"最新医生问题: {getattr(self, '_last_doctor_question', '暂无')[:50]}...")
        print("-" * 60)
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        获取当前工作流状态
        
        Returns:
            Dict: 工作流状态信息
        """
        return {
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "current_phase": self.task_manager.get_current_phase().value,
            "workflow_completed": self.workflow_completed,
            "workflow_success": self.workflow_success,
            "completion_summary": self.task_manager.get_completion_summary(),
            "conversation_length": len(self.conversation_history),
            "triage_info": self.current_triage,
            "log_file_path": self.logger.get_log_file_path()
        }
    
    def get_conversation_history(self) -> str:
        """
        获取完整的对话历史
        
        Returns:
            str: 对话历史
        """
        return self.conversation_history
    
    def get_medical_summary(self) -> Dict[str, str]:
        """
        获取当前医疗信息摘要
        
        Returns:
            Dict: 医疗信息摘要
        """
        return {
            "chief_complaint": self.current_chief_complaint,
            "history_of_present_illness": self.current_hpi,
            "past_history": self.current_ph,
            "triage_info": self.current_triage
        }