import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import hashlib

class WorkflowLogger:
    """
    工作流日志记录器
    负责将每个step的详细信息记录到jsonl格式文件中
    """
    
    def __init__(self, case_data: Dict[str, Any], log_dir: str = "logs", case_index: Optional[int] = None):
        """
        初始化日志记录器
        
        Args:
            case_data: 病例数据
            log_dir: 日志目录，默认为"logs"  
            case_index: 病例序号，用于文件名标识
        """
        self.case_data = case_data
        self.log_dir = log_dir
        self.case_index = case_index
        self.log_file_path = self._generate_log_file_path()
        self.step_count = 0
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 初始化日志文件，记录工作流开始信息
        self._log_workflow_start()
    
    def _generate_log_file_path(self) -> str:
        """
        为当前病例生成唯一的日志文件路径
        
        Returns:
            str: 日志文件路径
        """
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建文件名，如果有序号则包含序号
        if self.case_index is not None:
            filename = f"workflow_{timestamp}_case_{self.case_index:04d}.jsonl"
        else:
            # 生成基于病例内容的唯一标识作为后备
            case_str = json.dumps(self.case_data, ensure_ascii=False, sort_keys=True)
            case_hash = hashlib.md5(case_str.encode('utf-8')).hexdigest()[:8]
            filename = f"workflow_{timestamp}_{case_hash}.jsonl"
        
        return os.path.join(self.log_dir, filename)
    
    def _log_workflow_start(self):
        """记录工作流开始信息"""
        start_log = {
            "event_type": "workflow_start",
            "timestamp": datetime.now().isoformat(),
            "case_data": self.case_data,
            "workflow_config": {
                "max_steps": 30,
                "completion_threshold": 0.85,
                "phases": ["triage", "hpi", "ph"]
            }
        }
        self._write_log_entry(start_log)
    
    def log_step_start(self, step_num: int, current_phase: str, pending_tasks: list):
        """
        记录step开始信息
        
        Args:
            step_num: step编号
            current_phase: 当前阶段
            pending_tasks: 待完成任务列表
        """
        self.step_count = step_num
        step_start_log = {
            "event_type": "step_start",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "current_phase": current_phase,
            "pending_tasks": pending_tasks
        }
        self._write_log_entry(step_start_log)
    
    def log_patient_response(self, step_num: int, patient_message: str, is_first_step: bool = False):
        """
        记录患者回应
        
        Args:
            step_num: step编号
            patient_message: 患者消息
            is_first_step: 是否为第一个step
        """
        patient_log = {
            "event_type": "patient_response",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "is_first_step": is_first_step,
            "message": patient_message
        }
        self._write_log_entry(patient_log)
    
    def log_agent_execution(self, step_num: int, agent_name: str, 
                          input_data: Dict[str, Any], output_data: Dict[str, Any], 
                          execution_time: Optional[float] = None):
        """
        记录agent执行信息
        
        Args:
            step_num: step编号
            agent_name: agent名称
            input_data: 输入数据
            output_data: 输出数据
            execution_time: 执行时间（秒）
        """
        agent_log = {
            "event_type": "agent_execution",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "input_data": input_data,
            "output_data": output_data
        }
        
        if execution_time is not None:
            agent_log["execution_time_seconds"] = execution_time
            
        self._write_log_entry(agent_log)
    
    def log_task_scores_update(self, step_num: int, phase: str, 
                             old_scores: Dict[str, float], 
                             new_scores: Dict[str, float]):
        """
        记录任务评分更新
        
        Args:
            step_num: step编号
            phase: 阶段名称
            old_scores: 更新前的评分
            new_scores: 更新后的评分
        """
        scores_log = {
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
        }
        self._write_log_entry(scores_log)
    
    def log_step_complete(self, step_num: int, doctor_question: str, 
                         conversation_history: str, task_completion_summary: Dict):
        """
        记录step完成信息
        
        Args:
            step_num: step编号
            doctor_question: 医生生成的问题
            conversation_history: 对话历史
            task_completion_summary: 任务完成情况摘要
        """
        step_complete_log = {
            "event_type": "step_complete",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "doctor_question": doctor_question,
            "conversation_history": conversation_history,
            "task_completion_summary": task_completion_summary
        }
        self._write_log_entry(step_complete_log)
    
    def log_workflow_complete(self, total_steps: int, final_summary: Dict, success: bool = True):
        """
        记录工作流完成信息
        
        Args:
            total_steps: 总step数
            final_summary: 最终摘要
            success: 是否成功完成
        """
        complete_log = {
            "event_type": "workflow_complete",
            "timestamp": datetime.now().isoformat(),
            "total_steps": total_steps,
            "success": success,
            "final_summary": final_summary,
            "log_file_path": self.log_file_path
        }
        self._write_log_entry(complete_log)
    
    def log_error(self, step_num: int, error_type: str, error_message: str, 
                 error_context: Optional[Dict] = None):
        """
        记录错误信息
        
        Args:
            step_num: step编号
            error_type: 错误类型
            error_message: 错误消息
            error_context: 错误上下文
        """
        error_log = {
            "event_type": "error",
            "step_number": step_num,
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message
        }
        
        if error_context:
            error_log["error_context"] = error_context
            
        self._write_log_entry(error_log)
    
    def _write_log_entry(self, log_entry: Dict[str, Any]):
        """
        写入一条日志记录到jsonl文件
        
        Args:
            log_entry: 日志条目
        """
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"写入日志失败: {e}")
    
    def get_log_file_path(self) -> str:
        """
        获取日志文件路径
        
        Returns:
            str: 日志文件路径
        """
        return self.log_file_path
    
    def get_step_count(self) -> int:
        """
        获取当前step计数
        
        Returns:
            int: step计数
        """
        return self.step_count