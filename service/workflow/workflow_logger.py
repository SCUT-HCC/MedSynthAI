import logging
from datetime import datetime
from typing import Dict, Any, Optional

class WorkflowLogger:
    """
    工作流日志记录器（轻量版）
    - 移除 case_index 相关逻辑
    - 不再写入 jsonl 文件，仅使用标准日志输出
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        初始化日志记录器
        Args:
            log_dir: 保留参数以兼容旧接口，但不使用文件落盘
        """
        self.step_count = 0
        self.logger = logging.getLogger("WorkflowLogger")
        self._log_workflow_start()
    
    def _log_workflow_start(self):
        self.logger.info({
            "event_type": "workflow_start",
            "timestamp": datetime.now().isoformat(),
            "workflow_config": {
                "max_steps": 30,
                "completion_threshold": 0.85,
                "phases": ["triage", "hpi", "ph"]
            }
        })
    
    def log_step_start(self, step_num: int, current_phase: str, pending_tasks: list):
        self.step_count = step_num
        self.logger.info({
            "event_type": "step_start",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "current_phase": current_phase,
            "pending_tasks": pending_tasks
        })
    
    def log_patient_response(self, step_num: int, patient_message: str, is_first_step: bool = False):
        self.logger.info({
            "event_type": "patient_response",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "is_first_step": is_first_step,
            "message": patient_message
        })
    
    def log_agent_execution(self, step_num: int, agent_name: str, 
                            input_data: Dict[str, Any], output_data: Dict[str, Any], 
                            execution_time: Optional[float] = None):
        payload = {
            "event_type": "agent_execution",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "input_data": input_data,
            "output_data": output_data
        }
        if execution_time is not None:
            payload["execution_time_seconds"] = execution_time
        self.logger.info(payload)
    
    def log_task_scores_update(self, step_num: int, phase: str, 
                               old_scores: Dict[str, float], 
                               new_scores: Dict[str, float]):
        self.logger.info({
            "event_type": "task_scores_update",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "old_scores": old_scores,
            "new_scores": new_scores,
            "score_changes": {
                task: new_scores[task] - old_scores.get(task, 0.0) 
                for task in new_scores
            }
        })
    
    def log_step_complete(self, step_num: int, doctor_question: str, 
                          conversation_history: str, task_completion_summary: Dict):
        self.logger.info({
            "event_type": "step_complete",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "doctor_question": doctor_question,
            "conversation_history": conversation_history,
            "task_completion_summary": task_completion_summary
        })
    
    def log_workflow_complete(self, total_steps: int, final_summary: Dict, success: bool = True):
        self.logger.info({
            "event_type": "workflow_complete",
            "timestamp": datetime.now().isoformat(),
            "total_steps": total_steps,
            "success": success,
            "final_summary": final_summary
        })
    
    def log_error(self, step_num: int, error_type: str, error_message: str, 
                  error_context: Optional[Dict] = None):
        payload = {
            "event_type": "error",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message
        }
        if error_context:
            payload["error_context"] = error_context
        self.logger.error(payload)
    
    def get_log_file_path(self) -> str:
        """
        保留兼容方法，返回空字符串（不写文件）
        """
        return ""
    
    def get_step_count(self) -> int:
        return self.step_count