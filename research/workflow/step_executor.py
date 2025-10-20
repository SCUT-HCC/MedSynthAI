import time
from typing import Dict, Any, List, Optional
from agent_system.recipient import RecipientAgent
from agent_system.triager import TriageAgent
from agent_system.monitor import Monitor
from agent_system.controller import TaskController
from agent_system.prompter import Prompter
from agent_system.inquirer import Inquirer
from agent_system.virtual_patient import VirtualPatientAgent
from agent_system.evaluator import Evaluator
from .task_manager import TaskManager, TaskPhase
from .workflow_logger import WorkflowLogger
from guidance.loader import get_comparison_guidance, _update_guidance_for_Triager


class StepExecutor:
    """
    单step执行器
    负责执行单个step中的完整agent pipeline流程
    """
    
    # 全局变量存储历史评分
    _global_historical_scores = {
        "clinical_inquiry": 0.0,
        "communication_quality": 0.0,
        "information_completeness": 0.0,
        "overall_professionalism": 0.0,
        "present_illness_similarity": 0.0,
        "past_history_similarity": 0.0,
        "chief_complaint_similarity": 0.0
    }
    
    @classmethod
    def reset_historical_scores(cls):
        """重置全局历史评分"""
        cls._global_historical_scores = {
            "clinical_inquiry": 0.0,
            "communication_quality": 0.0,
            "information_completeness": 0.0,
            "overall_professionalism": 0.0,
            "present_illness_similarity": 0.0,
            "past_history_similarity": 0.0,
            "chief_complaint_similarity": 0.0
        }
    
    def __init__(self, model_type: str = "gpt-oss:latest", llm_config: dict = None, controller_mode: str = "normal"):
        """
        初始化step执行器
        
        Args:
            model_type: 使用的语言模型类型（除Evaluator外的所有agent使用）
            llm_config: 语言模型配置
            controller_mode: 任务控制器模式，'normal'为智能模式，'sequence'为顺序模式，'score_driven'为分数驱动模式
        
        Note:
            Evaluator agent 固定使用 gpt-oss:latest 模型，不受 model_type 参数影响
        """
        self.model_type = model_type
        self.llm_config = llm_config or {}
        self.controller_mode = controller_mode
        
        # 初始化所有agent
        self.recipient = RecipientAgent(model_type=model_type, llm_config=self.llm_config)
        self.triager = TriageAgent(model_type=model_type, llm_config=self.llm_config)
        self.monitor = Monitor(model_type=model_type, llm_config=self.llm_config)
        # 根据模式初始化TaskController
        simple_mode = (controller_mode == "sequence")
        score_driven_mode = (controller_mode == "score_driven")
        self.controller = TaskController(
            model_type=model_type, 
            llm_config=self.llm_config, 
            simple_mode=simple_mode,
            score_driven_mode=score_driven_mode
        )
        self.prompter = Prompter(model_type=model_type, llm_config=self.llm_config)
        self.virtual_patient = VirtualPatientAgent(model_type=model_type, llm_config=self.llm_config)
        # Evaluator 固定使用 gpt-oss:latest 模型
        self.evaluator = Evaluator(model_type="gpt-oss:latest", llm_config=self.llm_config)
    
    def execute_step(self, 
                    step_num: int,
                    case_data: Dict[str, Any],
                    task_manager: TaskManager,
                    logger: WorkflowLogger,
                    conversation_history: str = "",
                    previous_hpi: str = "",
                    previous_ph: str = "",
                    previous_chief_complaint: str = "",
                    previous_department: str = "",
                    previous_candidate_department = "",
                    current_guidance: str = "",
                    is_first_step: bool = False,
                    doctor_question: str = "") -> Dict[str, Any]:
        """
        执行单个step的完整流程
        
        Args:
            step_num: step编号
            case_data: 病例数据
            task_manager: 任务管理器
            logger: 日志记录器
            conversation_history: 对话历史
            previous_hpi: 上轮现病史
            previous_ph: 上轮既往史
            previous_chief_complaint: 上轮主诉
            previous_department: 上轮分诊主要科室
            previous_candidate_department: 上轮分诊候选科室
            current_guidance: 当前指导文本
            is_first_step: 是否为第一个step
            doctor_question: 医生问题（非首轮时）
            
        Returns:
            Dict: step执行结果，包含更新后的病史信息、医生问题、患者回应等
        """
        step_result = {
            "step_number": step_num,
            "success": False,
            "patient_response": "",
            "updated_hpi": previous_hpi,
            "updated_ph": previous_ph,
            "updated_chief_complaint": previous_chief_complaint,
            "triage_result": {
                "primary_department": "",
                "secondary_department": "",
                "triage_reasoning": "",
                "candidate_primary_department": "",
                "candidate_secondary_department": ""
            },
            "doctor_question": "",
            "conversation_history": conversation_history,
            "task_completion_summary": {},
            "errors": []
        }
        
        try:
            # 更新任务管理器的当前步骤
            task_manager.current_step = step_num
            
            # Step 1: 获取患者回应
            patient_response = self._get_patient_response(
                step_num, case_data, logger, is_first_step, doctor_question
            )
            step_result["patient_response"] = patient_response
            
            # 更新对话历史
            if is_first_step:
                updated_conversation = f"患者: {patient_response}"
            else:
                updated_conversation = conversation_history + f"\n医生: {doctor_question}\n患者: {patient_response}"
            step_result["conversation_history"] = updated_conversation
            
            # Step 2: 使用Recipient更新病史信息
            recipient_result = self._execute_recipient(
                step_num, logger, updated_conversation, previous_hpi, previous_ph, previous_chief_complaint
            )
            step_result.update({
                "updated_hpi": recipient_result.updated_HPI,
                "updated_ph": recipient_result.updated_PH, 
                "updated_chief_complaint": recipient_result.chief_complaint
            })
            
            # Step 3: 使用Triager进行科室分诊（仅当当前阶段是分诊阶段时）
            current_phase = task_manager.get_current_phase()
            
            if current_phase == TaskPhase.TRIAGE:
                # 当前处于分诊阶段
                triage_result = self._execute_triager(
                    step_num, logger, recipient_result
                )
                step_result["triage_result"] = {
                    "primary_department": triage_result.primary_department,
                    "secondary_department": triage_result.secondary_department,
                    "triage_reasoning": triage_result.triage_reasoning,
                    "candidate_primary_department": triage_result.candidate_primary_department,
                    "candidate_secondary_department": triage_result.candidate_secondary_department
                }

                department = f"{triage_result.primary_department}-{triage_result.secondary_department}"
                candidate_department = f"{triage_result.candidate_primary_department}-{triage_result.candidate_secondary_department}"
                self.previous_department = department
                self.previous_candidate_department = candidate_department

                # 根据预测科室动态更新指导
                new_guidance = self._update_guidance_for_Triager(department)

            else:
                # 分诊已完成或已超过分诊阶段，使用已有的分诊结果
                existing_triage = step_result.get("triage_result", {})
                step_result["triage_result"] = {
                    "primary_department": existing_triage.get("primary_department", "未知"),
                    "secondary_department": existing_triage.get("secondary_department", "未知"),
                    "triage_reasoning": existing_triage.get("triage_reasoning", "分诊已完成")
                }
            
            # Step 4: 使用Monitor评估任务完成度
            monitor_results = self._execute_monitor_by_phase(
                step_num, logger, task_manager, recipient_result, step_result.get("triage_result", {})
            )
            
            
            # Step 5: 更新任务分数
            self._update_task_scores(step_num, logger, task_manager, monitor_results)
            
            # Step 6: 使用Controller选择下一个任务
            controller_result = self._execute_controller(
                step_num, logger, task_manager, recipient_result
            )
            
            # Step 7: 使用Prompter生成询问策略
            prompter_result = self._execute_prompter(
                step_num, logger, recipient_result, controller_result
            )
            
            # Step 8: 使用Inquirer生成医生问题
            doctor_question = self._execute_inquirer(
                step_num, logger, recipient_result, prompter_result
            )
            step_result["doctor_question"] = doctor_question
            
            # Step 9: 使用Evaluator进行评分
            evaluator_result = self._execute_evaluator(
                step_num, logger, case_data, step_result
            )
            step_result["evaluator_result"] = evaluator_result
            
            # Step 10: 获取任务完成情况摘要
            step_result["task_completion_summary"] = task_manager.get_completion_summary()
            
            step_result["success"] = True
            
        except Exception as e:
            error_msg = f"Step {step_num} 执行失败: {str(e)}"
            step_result["errors"].append(error_msg)
            logger.log_error(step_num, "step_execution_error", error_msg, {"case_data": case_data})
            print(error_msg)
        
        return step_result
    
    def _get_patient_response(self, step_num: int, case_data: Dict[str, Any], 
                             logger: WorkflowLogger, is_first_step: bool, 
                             doctor_question: str = "") -> str:
        """获取虚拟患者的回应"""
        start_time = time.time()
        
        try:
            # 构建虚拟患者输入
            if is_first_step:
                worker_inquiry = "您好，请问您哪里不舒服？"
            else:
                worker_inquiry = doctor_question
            
            # 调用虚拟患者agent
            patient_result = self.virtual_patient.run(
                worker_inquiry=worker_inquiry,
                is_first_epoch=is_first_step,
                patient_case=case_data
            )
            
            execution_time = time.time() - start_time
            patient_response = patient_result.current_chat
            
            # 记录日志
            logger.log_agent_execution(
                step_num, "virtual_patient",
                {
                    "worker_inquiry": worker_inquiry,
                    "is_first_epoch": is_first_step,
                    "case_data": case_data
                },
                {"patient_response": patient_response},
                execution_time
            )
            
            logger.log_patient_response(step_num, patient_response, is_first_step)
            
            return patient_response
            
        except Exception as e:
            error_msg = f"虚拟患者执行失败: {str(e)}"
            logger.log_error(step_num, "virtual_patient_error", error_msg)
            # 返回默认回应
            return "对不起，我不太清楚怎么描述，医生您看着办吧。"
    
    def _execute_recipient(self, step_num: int, logger: WorkflowLogger, 
                          conversation_history: str, previous_hpi: str, 
                          previous_ph: str, previous_chief_complaint: str):
        """执行Recipient agent"""
        start_time = time.time()
        
        input_data = {
            "conversation_history": conversation_history,
            "previous_HPI": previous_hpi,
            "previous_PH": previous_ph,
            "previous_chief_complaint": previous_chief_complaint
        }
        
        result = self.recipient.run(**input_data)
        execution_time = time.time() - start_time
        
        output_data = {
            "updated_HPI": result.updated_HPI,
            "updated_PH": result.updated_PH,
            "chief_complaint": result.chief_complaint
        }
        
        logger.log_agent_execution(step_num, "recipient", input_data, output_data, execution_time)
        
        return result
    
    def _execute_triager(self, step_num: int, logger: WorkflowLogger, 
                        recipient_result):
        """执行Triage agent进行科室分诊"""
        start_time = time.time()
        
        #构建department_comparison_guidance
        comparison_guidance = ""   
        # 如果存在上一轮的分诊结果，并且有主要科室和候选科室，则生成对比指导
        if self.previous_department and self.previous_candidate_department:
            comparison_guidance = get_comparison_guidance(previous_department, previous_candidate_department)
        
        # 将对比指导与常规指导合并
            combined_guidance = self.current_guidance
            if comparison_guidance:
                combined_guidance += f"\n\n【科室对比鉴别指导】\n{comparison_guidance}"

        input_data = {
            "chief_complaint": recipient_result.chief_complaint,
            "hpi_content": recipient_result.updated_HPI,
            "ph_content": recipient_result.updated_PH,
            "combined_guidance": combined_guidance,
        }
        
        result = self.triager.run(**input_data)
        execution_time = time.time() - start_time
        
        output_data = {
            "primary_department": result.primary_department,
            "secondary_department": result.secondary_department,
            "triage_reasoning": result.triage_reasoning,
            "candidate_primary_department": result.candidate_primary_department,
            "candidate_secondary_department": result.candidate_secondary_department,
        }
        #在日志中加入对比指导信息
        log_input_data = input_data.copy()
        log_input_data["used_comparison_guidance"] = bool(comparison_guidance)
        logger.log_agent_execution(step_num, "triager", input_data, output_data, execution_time)
        
        return result
    
    def _execute_monitor_by_phase(self, step_num: int, logger: WorkflowLogger, 
                                 task_manager: TaskManager, recipient_result, triage_result: Dict[str, Any] = None) -> Dict[str, Dict[str, float]]:
        """按阶段执行Monitor评估，只评估当前阶段未完成的任务"""
        monitor_results = {}
        current_phase = task_manager.get_current_phase()
        
        # 如果所有任务都完成了，不需要评估
        if current_phase == TaskPhase.COMPLETED:
            return monitor_results
        
        # 获取当前阶段未完成的任务
        pending_tasks = task_manager.get_pending_tasks(current_phase)
        if not pending_tasks:
            return monitor_results
        
        start_time = time.time()
        
        try:
            # 使用for循环逐个评估所有未完成的任务
            phase_scores = {}
            for task in pending_tasks:
                task_name = task.get("name", "")
                task_description = task.get("description", "")
                
                # 调用Monitor评估特定任务
                # 分诊阶段传入triage_result，其他阶段不传入
                if current_phase == TaskPhase.TRIAGE:
                    # 使用传入的triage_result
                    monitor_result = self.monitor.run(
                        hpi_content=recipient_result.updated_HPI,
                        ph_content=recipient_result.updated_PH,
                        chief_complaint=recipient_result.chief_complaint,
                        task_name=task_name,
                        task_description=task_description,
                        triage_result=triage_result if triage_result and triage_result.get("primary_department") else None
                    )
                else:
                    # 现病史/既往史阶段不传入triage_result
                    monitor_result = self.monitor.run(
                        hpi_content=recipient_result.updated_HPI,
                        ph_content=recipient_result.updated_PH,
                        chief_complaint=recipient_result.chief_complaint,
                        task_name=task_name,
                        task_description=task_description
                    )
                
                phase_scores[task_name] = monitor_result.completion_score
                print(f"任务'{task_name}'评分: {monitor_result.completion_score:.2f} - {monitor_result.reason}")
            
            execution_time = time.time() - start_time
            monitor_results[current_phase] = phase_scores
            
            # 记录日志
            input_data = {
                "hpi_content": recipient_result.updated_HPI,
                "ph_content": recipient_result.updated_PH,
                "chief_complaint": recipient_result.chief_complaint,
                "evaluated_phase": current_phase.value,
                "pending_tasks": [t["name"] for t in pending_tasks]
            }
            
            output_data = {
                "phase_scores": phase_scores,
                "evaluated_tasks": list(phase_scores.keys()),
                "average_score": sum(phase_scores.values()) / len(phase_scores) if phase_scores else 0.0
            }
            
            logger.log_agent_execution(step_num, "monitor", input_data, output_data, execution_time)
            
        except Exception as e:
            error_msg = f"Monitor执行失败: {str(e)}"
            logger.log_error(step_num, "monitor_error", error_msg)
            # 返回默认的低分评估
            phase_scores = {task["name"]: 0.1 for task in pending_tasks}
            monitor_results[current_phase] = phase_scores
        
        return monitor_results
    
    def _update_task_scores(self, step_num: int, logger: WorkflowLogger, 
                           task_manager: TaskManager, monitor_results: Dict):
        """更新任务分数"""
        for phase, scores in monitor_results.items():
            if scores:
                old_scores = task_manager.get_task_scores(phase).copy()
                task_manager.update_task_scores(phase, scores)
                new_scores = task_manager.get_task_scores(phase)
                
                logger.log_task_scores_update(step_num, phase.value, old_scores, new_scores)
    
    def _execute_controller(self, step_num: int, logger: WorkflowLogger, 
                           task_manager: TaskManager, recipient_result):
        """执行Controller agent"""
        start_time = time.time()
        
        # 获取当前阶段的未完成任务
        current_phase = task_manager.get_current_phase()
        pending_tasks = task_manager.get_pending_tasks(current_phase)
        
        input_data = {
            "pending_tasks": pending_tasks,
            "chief_complaint": recipient_result.chief_complaint,
            "hpi_content": recipient_result.updated_HPI,
            "ph_content": recipient_result.updated_PH,
            "task_manager": task_manager  # 传递task_manager用于score_driven模式
        }
        
        result = self.controller.run(**input_data)
        execution_time = time.time() - start_time
        
        # 为日志记录创建可序列化的input_data副本（移除TaskManager对象）
        log_input_data = {
            "pending_tasks": input_data["pending_tasks"],
            "chief_complaint": input_data["chief_complaint"],
            "hpi_content": input_data["hpi_content"],
            "ph_content": input_data["ph_content"]
            # 不包含task_manager，因为它不能JSON序列化
        }
        
        output_data = {
            "selected_task": result.selected_task,
            "specific_guidance": result.specific_guidance
        }
        
        logger.log_agent_execution(step_num, "controller", log_input_data, output_data, execution_time)
        
        return result
    
    def _execute_prompter(self, step_num: int, logger: WorkflowLogger, 
                         recipient_result, controller_result):
        """执行Prompter agent"""
        start_time = time.time()
        
        input_data = {
            "hpi_content": recipient_result.updated_HPI,
            "ph_content": recipient_result.updated_PH,
            "chief_complaint": recipient_result.chief_complaint,
            "current_task": controller_result.selected_task,
            "specific_guidance": controller_result.specific_guidance
        }
        
        result = self.prompter.run(**input_data)
        execution_time = time.time() - start_time
        
        output_data = {
            "description": result.description,
            "instructions": result.instructions
        }
        
        logger.log_agent_execution(step_num, "prompter", input_data, output_data, execution_time)
        
        return result
    
    def _execute_inquirer(self, step_num: int, logger: WorkflowLogger, 
                         recipient_result, prompter_result) -> str:
        """执行Inquirer agent"""
        start_time = time.time()

        try:
            if new_guidance != self.current_guidance:
                self.current_guidance = new_guidance
        
            # 使用Prompter生成的描述和指令初始化Inquirer
            inquirer = Inquirer(
                description=prompter_result.description,
                instructions=prompter_result.instructions,
                model_type=self.model_type,
                llm_config=self.llm_config,
                department_inquiry_guidance=new_guidance,
            )
            # print(f"🔄 已切换到 '{first_department}' 科室的询问指导")
            
            input_data = {
                "hpi_content": recipient_result.updated_HPI,
                "ph_content": recipient_result.updated_PH,
                "chief_complaint": recipient_result.chief_complaint
            }
            
            result = inquirer.run(**input_data)
            execution_time = time.time() - start_time
            
            doctor_question = result.current_chat
            
            output_data = {"doctor_question": doctor_question}
            
            logger.log_agent_execution(step_num, "inquirer", input_data, output_data, execution_time)
            
            return doctor_question
            
        except Exception as e:
            error_msg = f"Inquirer执行失败: {str(e)}"
            logger.log_error(step_num, "inquirer_error", error_msg)
            # 返回默认问题
            return "请您详细描述一下您的症状，包括什么时候开始的，有什么特点？"

    
    def _execute_evaluator(self, step_num: int, logger: WorkflowLogger, 
                          case_data: Dict[str, Any], step_result: Dict[str, Any]):
        """执行Evaluator agent"""
        start_time = time.time()
        
        try:
            # 准备评价器需要的数据格式，包含完整对话历史
            conversation_history = step_result.get("conversation_history", "")
            round_data = {
                "patient_response": step_result.get("patient_response", ""),
                "doctor_inquiry": step_result.get("doctor_question", ""),
                "HPI": step_result.get("updated_hpi", ""),
                "PH": step_result.get("updated_ph", ""),
                "chief_complaint": step_result.get("updated_chief_complaint", "")
            }
            
            # 使用全局历史评分
            historical_scores = self._global_historical_scores
            
            # 调用评价器进行评价，传入完整对话历史和历史评分
            input_data = {
                "patient_case": case_data,
                "current_round": step_num,
                "round_data": round_data,
                "conversation_history": conversation_history,
                "historical_scores": historical_scores  # 添加历史评分作为明确参数
            }
            
            # 构建所有轮次的数据用于多轮评估
            all_rounds_data = []
            
            # 从对话历史中提取每轮数据
            lines = conversation_history.strip().split('\n')
            current_round_data = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('医生:') and current_round_data:
                    # 完成上轮，开始新轮
                    all_rounds_data.append(current_round_data)
                    current_round_data = {"doctor_inquiry": line[3:].strip(), "patient_response": ""}
                elif line.startswith('医生:'):
                    # 新轮开始
                    current_round_data = {"doctor_inquiry": line[3:].strip(), "patient_response": ""}
                elif line.startswith('患者:') and current_round_data:
                    current_round_data["patient_response"] = line[3:].strip()
                elif line.startswith('患者:'):
                    # 第一轮只有患者回应
                    current_round_data = {"doctor_inquiry": "", "patient_response": line[3:].strip()}
            
            # 添加最后一轮
            if current_round_data:
                current_round_data.update({
                    "HPI": step_result.get("updated_hpi", ""),
                    "PH": step_result.get("updated_ph", ""),
                    "chief_complaint": step_result.get("updated_chief_complaint", "")
                })
                all_rounds_data.append(current_round_data)
            
            # 为所有轮次添加evaluation_scores，使用全局历史评分
            for i, round_data in enumerate(all_rounds_data):
                if i < step_num - 1:  # 历史轮次
                    # 使用全局历史评分
                    round_data["evaluation_scores"] = self._global_historical_scores
                else:  # 当前轮次
                    # 当前轮次尚未评分，使用空值占位
                    round_data["evaluation_scores"] = {
                        "clinical_inquiry": 0.0,
                        "communication_quality": 0.0,
                        "information_completeness": 0.0,
                        "overall_professionalism": 0.0,
                        "present_illness_similarity": 0.0,
                        "past_history_similarity": 0.0,
                        "chief_complaint_similarity": 0.0
                    }
            
            # 调用支持多轮的评估方法
            result = self.evaluator.run(
                patient_case=case_data,
                current_round=step_num,
                all_rounds_data=all_rounds_data,
                historical_scores=historical_scores
            )
            
            execution_time = time.time() - start_time
            
            output_data = {
                "clinical_inquiry": {
                    "score": result.clinical_inquiry.score,
                    "comment": result.clinical_inquiry.comment
                },
                "communication_quality": {
                    "score": result.communication_quality.score,
                    "comment": result.communication_quality.comment
                },
                "information_completeness": {
                    "score": result.information_completeness.score,
                    "comment": result.information_completeness.comment
                },
                "overall_professionalism": {
                    "score": result.overall_professionalism.score,
                    "comment": result.overall_professionalism.comment
                },
                "present_illness_similarity": {
                    "score": result.present_illness_similarity.score,
                    "comment": result.present_illness_similarity.comment
                },
                "past_history_similarity": {
                    "score": result.past_history_similarity.score,
                    "comment": result.past_history_similarity.comment
                },
                "chief_complaint_similarity": {
                    "score": result.chief_complaint_similarity.score,
                    "comment": result.chief_complaint_similarity.comment
                },
                "summary": result.summary,
                "key_suggestions": result.key_suggestions
            }
            
            logger.log_agent_execution(step_num, "evaluator", input_data, output_data, execution_time)
            
            # 更新全局历史评分
            self._global_historical_scores = {
                "clinical_inquiry": result.clinical_inquiry.score,
                "communication_quality": result.communication_quality.score,
                "information_completeness": result.information_completeness.score,
                "overall_professionalism": result.overall_professionalism.score,
                "present_illness_similarity": result.present_illness_similarity.score,
                "past_history_similarity": result.past_history_similarity.score,
                "chief_complaint_similarity": result.chief_complaint_similarity.score
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Evaluator执行失败: {str(e)}"
            logger.log_error(step_num, "evaluator_error", error_msg)
            # 返回默认评价结果
            from agent_system.evaluator.response_model import EvaluatorResult, EvaluationDimension
            
            default_dimension = EvaluationDimension(score=0.0, comment="评价失败")
            return EvaluatorResult(
                clinical_inquiry=default_dimension,
                communication_quality=default_dimension,
                information_completeness=default_dimension,
                overall_professionalism=default_dimension,
                present_illness_similarity=default_dimension,
                past_history_similarity=default_dimension,
                chief_complaint_similarity=default_dimension,
                summary="评价失败",
                key_suggestions=["系统需要调试"]
            )