from typing import Dict, List, Optional
from enum import Enum

class TaskPhase(Enum):
    """任务阶段枚举"""
    TRIAGE = "triage"  # 分诊阶段
    HPI = "hpi"        # 现病史阶段  
    PH = "ph"          # 既往史阶段
    COMPLETED = "completed"  # 全部完成

class TaskManager:
    """
    任务管理器
    负责管理分诊、现病史、既往史三个阶段的子任务状态和完成度评分
    """
    
    def __init__(self):
        """初始化任务管理器"""
        self.completion_threshold = 0.85  # 任务完成阈值
        self.current_step = 1  # 当前步骤计数器
        
        # 定义各阶段的子任务
        self.task_definitions = {
            TaskPhase.TRIAGE: {
                "一级科室判定": {"description": "确定患者应就诊的一级科室（如内科、外科等）"},
                "二级科室判定": {"description": "在一级科室基础上确定具体的二级科室"}
            },
            TaskPhase.HPI: {
                "发病情况": {"description": "记录发病的时间、地点、起病缓急、前驱症状、可能的原因或诱因"},
                "主要症状特征": {"description": "按发生的先后顺序描述主要症状的部位、性质、持续时间、程度、缓解或加剧因素"},
                "病情发展与演变": {"description": "按发生的先后顺序描述演变发展情况"},
                "伴随症状": {"description": "记录伴随症状，描述伴随症状与主要症状之间的相互关系"},
                "诊疗经过": {"description": "记录患者发病后是否接受过检查与治疗，若是则记录接受过的检查与治疗的经过及效果"},
                "一般情况": {"description": "简要记录患者发病后的精神状态、睡眠、食欲、大小便、体重等情况"}
            },
            TaskPhase.PH: {
                "疾病史": {"description": "详细询问患者既往患过的各种疾病史，包括传染病史如结核、肝炎等"},
                "预防接种史": {"description": "询问患者疫苗接种情况"},
                "手术外伤史": {"description": "记录患者既往手术史和外伤史"},
                "输血史": {"description": "询问患者既往输血史及输血反应"},
                "过敏史": {"description": "了解患者食物或药物过敏史等"}
            }
        }
        
        # 初始化任务完成度评分（所有任务初始分数为0.0）
        self.task_scores = {}
        for phase in self.task_definitions:
            self.task_scores[phase] = {}
            for task_name in self.task_definitions[phase]:
                self.task_scores[phase][task_name] = 0.0
    
    def update_step(self, step_num: int):
        """
        更新当前步骤编号
        
        Args:
            step_num: 当前步骤编号
        """
        self.current_step = step_num
    
    def get_current_phase(self) -> TaskPhase:
        """
        获取当前应该执行的任务阶段
        分诊阶段限制最多4步，第5步开始即使未完成也进入现病史阶段
        
        Returns:
            TaskPhase: 当前任务阶段
        """
        # 检查分诊阶段是否完成，且不超过4步
        if not self._is_phase_completed(TaskPhase.TRIAGE) and self.current_step <= 4:
            return TaskPhase.TRIAGE
        
        # 如果超过4步或分诊已完成，进入现病史阶段
        if not self._is_phase_completed(TaskPhase.HPI):
            return TaskPhase.HPI
            
        # 检查既往史阶段是否完成
        if not self._is_phase_completed(TaskPhase.PH):
            return TaskPhase.PH
            
        # 所有阶段都完成
        return TaskPhase.COMPLETED
    
    def get_pending_tasks(self, phase: Optional[TaskPhase] = None) -> List[Dict[str, str]]:
        """
        获取指定阶段的未完成任务列表
        
        Args:
            phase: 指定的任务阶段，如果为None则获取当前阶段
            
        Returns:
            List[Dict]: 未完成任务列表，每个任务包含name和description字段
        """
        if phase is None:
            phase = self.get_current_phase()
        
        if phase == TaskPhase.COMPLETED:
            return []
        
        pending_tasks = []
        phase_tasks = self.task_definitions[phase]
        phase_scores = self.task_scores[phase]
        
        for task_name, task_info in phase_tasks.items():
            if phase_scores[task_name] < self.completion_threshold:
                pending_tasks.append({
                    "name": task_name,
                    "description": task_info["description"]
                })
        
        return pending_tasks
    
    def update_task_scores(self, phase: TaskPhase, task_scores: Dict[str, float]):
        """
        更新指定阶段的任务完成度评分
        
        Args:
            phase: 任务阶段
            task_scores: 任务评分字典，格式为 {任务名: 评分}
        """
        if phase not in self.task_scores:
            return
        
        for task_name, score in task_scores.items():
            if task_name in self.task_scores[phase]:
                self.task_scores[phase][task_name] = score
    
    def get_task_scores(self, phase: Optional[TaskPhase] = None) -> Dict:
        """
        获取任务评分信息
        
        Args:
            phase: 指定的任务阶段，如果为None则返回所有阶段
            
        Returns:
            Dict: 任务评分信息
        """
        if phase is None:
            return self.task_scores
        return self.task_scores.get(phase, {})
    
    def get_completion_summary(self) -> Dict[str, any]:
        """
        获取任务完成情况摘要
        
        Returns:
            Dict: 完成情况摘要，包含各阶段完成状态和进度
        """
        summary = {
            "current_phase": self.get_current_phase().value,
            "phases": {}
        }
        
        for phase, tasks in self.task_definitions.items():
            completed_count = sum(
                1 for task_name in tasks 
                if self.task_scores[phase][task_name] >= self.completion_threshold
            )
            total_count = len(tasks)
            
            summary["phases"][phase.value] = {
                "completed": completed_count,
                "total": total_count,
                "completion_rate": completed_count / total_count if total_count > 0 else 0,
                "is_completed": self._is_phase_completed(phase)
            }
        
        return summary
    
    def _is_phase_completed(self, phase: TaskPhase) -> bool:
        """
        检查指定阶段是否完成
        
        Args:
            phase: 任务阶段
            
        Returns:
            bool: 是否完成
        """
        if phase not in self.task_scores:
            return False
        
        phase_scores = self.task_scores[phase]
        return all(score >= self.completion_threshold for score in phase_scores.values())
    
    def is_workflow_completed(self) -> bool:
        """
        检查整个工作流是否完成
        
        Returns:
            bool: 是否完成
        """
        return self.get_current_phase() == TaskPhase.COMPLETED