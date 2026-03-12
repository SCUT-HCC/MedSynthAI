from fastapi import APIRouter, HTTPException
from service.Model.report import ReportModel
from service.workflow.medical_workflow import MedicalWorkflow
import logging

# 从 api_chat 导入共享的会话状态
from service.API.api_chat import sessions

router = APIRouter()
report_db = ReportModel()

@router.get("/dialogue/report")
async def get_medical_report(session_id: str):
    """
    获取病历报告接口
    逻辑：
    1. 优先尝试从数据库读取（通常是已完成的最终报告）。
    2. 如果数据库没有，尝试从内存中的活跃会话读取（生成实时临时报告）。
    """
    print(f"[DEBUG] 收到报告请求 - Session ID: {session_id}")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    # --- 1. 尝试从数据库获取 (最终报告) ---
    try:
        db_report = report_db.get_report_by_session(session_id)
        if db_report:
            print(f"[DEBUG] 从数据库找到报告: {session_id}")
            return {
                "分诊结果": db_report.get('triage_result', '尚未生成'),
                "主诉": db_report.get('chief_complaint', '尚未生成'),
                "现病史": db_report.get('hpi', '尚未生成'),
                "既往史": db_report.get('past_history', '尚未生成'),
                "状态": "已归档"
            }
    except Exception as e:
        logging.error(f"Database read failed: {e}")

    # --- 2. 尝试从内存获取 (实时/临时报告) ---
    if session_id in sessions:
        print(f"[DEBUG] 从内存生成实时报告: {session_id}")
        session_data = sessions[session_id]
        workflow: MedicalWorkflow = session_data["workflow"]
        
        # 格式化分诊结果
        triage_data = workflow.current_triage or {}
        primary = triage_data.get('primary_department', '')
        secondary = triage_data.get('secondary_department', '')
        
        if primary:
            triage_str = f"{primary}" + (f" - {secondary}" if secondary else "")
        else:
            triage_str = "分析中..."

        return {
            "分诊结果": triage_str,
            "主诉": workflow.current_chief_complaint or "信息收集中...",
            "现病史": workflow.current_hpi or "信息收集中...",
            "既往史": workflow.current_ph or "信息收集中...",
            "状态": "进行中"
        }
    
    # --- 3. 均未找到 ---
    print(f"[WARN] 报告未找到: {session_id}")
    # 为了不让前端报错，可以返回一个空报告结构，而不是 404
    return {
        "分诊结果": "未找到记录",
        "主诉": "未找到记录",
        "现病史": "未找到记录",
        "既往史": "未找到记录",
        "状态": "未知"
    }