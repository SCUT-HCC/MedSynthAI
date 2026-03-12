import uuid
import argparse
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

# 导入业务模块
from service.main import prepare_for_interactive, setup_logging
from service.workflow.medical_workflow import MedicalWorkflow
from service.workflow.workflow_logger import WorkflowLogger
from research.config import LLM_CONFIG

# 导入数据库模型
from service.Model.Chat import ChatModel, ChatRequest, ChatResponse
from service.Model.report import ReportModel

# 创建路由器
router = APIRouter()

# --- 全局变量 ---
# 1. 数据库实例 (保持连接)
chat_db = ChatModel()
report_db = ReportModel()

# 2. 会话状态存储 (内存，用于维持工作流对象状态)
# 注意：这个变量会被 api_report.py 引用
sessions: Dict[str, Dict] = {}

def get_default_args():
    """构造默认配置参数"""
    args = argparse.Namespace()
    args.department_guidance_file = 'guidance/department_inquiry_guidance.json'
    args.comparison_rules_file = 'guidance/department_comparison_guidance.json'
    args.log_dir = 'results/api_logs'
    args.max_steps = 30
    args.department_filter = None
    args.use_inquiry_guidance = True
    args.use_dynamic_guidance = True
    args.use_department_comparison = True
    
    default_model = "deepseek"
    if default_model not in LLM_CONFIG:
        if LLM_CONFIG:
            default_model = list(LLM_CONFIG.keys())[0]
        else:
            raise ValueError("LLM_CONFIG is empty in config.py")
            
    args.model_type = default_model
    args.controller_mode = 'normal'
    args.log_level = 'INFO'
    
    setup_logging(args.log_dir, args.log_level)
    return args

@router.post("/api/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest):
    """问诊交互接口"""
    session_id = request.session_id
    patient_content = request.patient_content
    
    print(f"[DEBUG] 收到请求 - SessionID: {session_id}, Content: {patient_content}")
    
    # --- A. 会话初始化逻辑 (修改版) ---
    # 触发初始化的条件：
    # 1. 前端没传 session_id (新用户)
    # 2. 前端传了 session_id，但后端内存里没有 (服务器重启导致丢失)
    need_init = False
    
    if not session_id:
        # 情况1: 全新会话
        session_id = str(uuid.uuid4())
        need_init = True
    elif session_id not in sessions:
        # 情况2: 服务器重启或会话过期，但前端还记着旧ID
        print(f"[WARN] 会话 {session_id} 在内存中不存在（可能是服务器重启），正在重新初始化...")
        # 我们可以选择沿用旧ID，这样前端不需要改动，用户体验更流畅
        need_init = True
    
    if need_init:
        try:
            args = get_default_args()
            workflow = prepare_for_interactive(args)
            
            if not hasattr(workflow, 'logger'):
                workflow.logger = WorkflowLogger(log_dir=args.log_dir)
            
            sessions[session_id] = {
                "workflow": workflow,
                "args": args,
                "step_count": 0
            }
            print(f"[INFO] 会话 {session_id} 初始化成功")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Workflow initialization failed: {str(e)}")
    
    # --- B. 获取会话上下文 ---
    # 此时 session_id 肯定在 sessions 里了
    session_data = sessions[session_id]
    workflow: MedicalWorkflow = session_data["workflow"]
    args = session_data["args"]
    
    current_step = session_data["step_count"] + 1
    session_data["step_count"] = current_step
    
    # [DB] 保存患者输入
    try:
        chat_db.save_record(session_id, "patient", patient_content, current_step)
    except Exception as e:
        logging.error(f"Failed to save patient record: {e}")

    # --- C. 检查结束条件 ---
    task_manager = workflow.task_manager
    if task_manager.is_workflow_completed() or current_step > args.max_steps:
        return ChatResponse(
            session_id=session_id,
            worker_inquiry="问诊已结束，感谢您的配合。",
            is_completed=True,
        )

    # --- D. 执行单步逻辑 ---
    logger = workflow.logger
    step_executor = workflow.step_executor

    task_manager.update_step(current_step)
    current_phase = task_manager.get_current_phase()
    pending_tasks = task_manager.get_pending_tasks(current_phase)
    logger.log_step_start(current_step, current_phase.value, pending_tasks)

    last_doctor_question = getattr(workflow, "_last_doctor_question", "")

    try:
        step_result = step_executor.execute_step(
            step_num=current_step,
            task_manager=task_manager,
            logger=logger,
            conversation_history=workflow.conversation_history,
            previous_hpi=workflow.current_hpi,
            previous_ph=workflow.current_ph,
            previous_chief_complaint=workflow.current_chief_complaint,
            previous_department=f"{workflow.current_triage.get('primary_department','')}-{workflow.current_triage.get('secondary_department','')}",
            previous_candidate_department=f"{workflow.current_triage.get('candidate_primary_department','')}-{workflow.current_triage.get('candidate_secondary_department','')}",
            previous_triage_reasoning=workflow.current_triage.get("triage_reasoning", ""),
            current_guidance=workflow.current_guidance if hasattr(workflow, 'current_guidance') else "",
            patient_response=patient_content,
            is_first_step=(current_step == 1),
            doctor_question=last_doctor_question
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal processing error: {str(e)}")

    if not step_result.get("success", False):
        error_msg = f"Step {current_step} execution failed: {step_result.get('errors')}"
        logger.log_error(current_step, "execution_error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    # 更新工作流状态
    workflow._update_workflow_state(step_result)
    
    # 准备返回数据
    worker_inquiry = step_result.get("doctor_question", "请问还有什么需要补充的吗？")
    is_completed = task_manager.is_workflow_completed()

    # [DB] 保存医生回复
    try:
        chat_db.save_record(session_id, "doctor", worker_inquiry, current_step)
    except Exception as e:
        logging.error(f"Failed to save doctor record: {e}")

    # 如果问诊结束，保存报告到数据库
    if is_completed:
        final_summary = task_manager.get_completion_summary()
        logger.log_workflow_complete(total_steps=current_step, final_summary=final_summary, success=True)
        worker_inquiry = "问诊结束，感谢您的配合。"
        
        # 格式化分诊结果
        triage_data = workflow.current_triage or {}
        primary = triage_data.get('primary_department', '')
        secondary = triage_data.get('secondary_department', '')
        triage_str = f"{primary}" + (f" - {secondary}" if secondary else "") if primary else "尚未生成"

        # [DB] 保存最终报告
        try:
            report_db.save_report(
                session_id=session_id,
                chief_complaint=workflow.current_chief_complaint or "尚未生成",
                hpi=workflow.current_hpi or "尚未生成",
                past_history=workflow.current_ph or "尚未生成",
                triage_result=triage_str
            )
        except Exception as e:
            logging.error(f"Failed to save medical report: {e}")

    return ChatResponse(
        session_id=session_id,
        worker_inquiry=worker_inquiry,
        is_completed=is_completed,
    )