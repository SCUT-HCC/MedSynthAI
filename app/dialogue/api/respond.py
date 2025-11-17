import uuid
import re
import html
import asyncio
import logging
import time
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel   # 新增，用于定义请求/响应模型

from medsynthai.workflows import MedicalWorkflow  #统一的工作流
from medsynthai.database_model import (
    DialogueDatabase,
)

respond_router = APIRouter()
logger = logging.getLogger(__name__)

# 最大输入长度限制 (字符数)
MAX_INPUT_LENGTH = 3000
# 超时限制 (秒)
WORKFLOW_TIMEOUT = 1000

#新的请求/响应模型
class RespondRequest(BaseModel):
     session_id: str
     patient_content: str

class RespondResponse(BaseModel):
    session_id: str
    doctor_content: str


# 依赖项：获取对话数据库和分诊工作流
def get_dialogue_db(request: Request):
    return request.app.state.dialogue_db

def get_medical_workflows(request: Request):
    return request.app.state.medical_workflows

def get_medical_workflows_lock(request: Request):
    return request.app.state.medical_workflows_lock


# 输入清理函数
def sanitize_input(text: str) -> str:
    """清理输入文本中的潜在有害内容"""
    if not text:
        return ""
    
    # 移除HTML标签
    text = html.escape(text)
    
    # 简单的SQL注入防护 (移除SQL关键字)
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'UNION']
    pattern = r'\b(' + '|'.join(sql_keywords) + r')\b'
    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text

# 验证UUID格式
def is_valid_uuid(id_string):
    """检查字符串是否是有效的UUID格式"""
    try:
        uuid_obj = uuid.UUID(id_string)
        return True
    except (ValueError, AttributeError, TypeError):
        return False

# 错误恢复回复
DEFAULT_ERROR_RESPONSE = "很抱歉，我需要更多信息来理解您的症状。请描述一下您的主要不适症状，例如症状的性质、位置、严重程度以及持续时间。"

@respond_router.post("/respond", response_model=RespondResponse)
async def respond(
    request: RespondRequest,
    dialogue_db: DialogueDatabase = Depends(get_dialogue_db),
    medical_workflows: dict = Depends(get_medical_workflows),
    medical_workflows_lock: asyncio.Lock = Depends(get_medical_workflows_lock)
):
    try:
        # 预处理及输入验证
        pre_process_start_time = time.time()
        
        # 验证session_id格式
        if not hasattr(request, 'session_id') or not request.session_id:
            # 缺少session_id
            raise HTTPException(status_code=400, detail="Missing session_id")
        
        session_id = request.session_id
        if not is_valid_uuid(session_id):
            # 无效的session_id格式
            raise HTTPException(status_code=400, detail="Invalid session_id format. Must be a valid UUID.")
        
        # 处理patient_content
        if not hasattr(request, 'patient_content'):
            raise HTTPException(status_code=400, detail="Missing patient_content")
        
        patient_content = request.patient_content or ""
        
        # 清理输入
        patient_content = sanitize_input(patient_content)
        
        # 检查输入长度
        if len(patient_content) > MAX_INPUT_LENGTH:
            logger.warning(f"Input too long ({len(patient_content)} chars), truncating to {MAX_INPUT_LENGTH} chars")
            patient_content = patient_content[:MAX_INPUT_LENGTH] + "..."
        
        # 如果输入为空，返回引导消息
        if not patient_content.strip():
            return RespondResponse(
                session_id=session_id,
                doctor_content="请描述您的症状，以便我们进行初步诊断。您可以告诉我您感觉不舒服的地方、症状开始的时间、严重程度等信息。"
            )
        
        # 获取或创建工作流
        workflow = medical_workflows.get(session_id)
        if workflow is None:
            workflow = MedicalWorkflow()
            async with medical_workflows_lock:
                medical_workflows[session_id] = workflow
        
        pre_process_end_time = time.time()
        logger.info(f"Pre-process time: {pre_process_end_time - pre_process_start_time:.2f} seconds")

        # 预诊断处理
        workflow_start_time = time.time()
        
        # 设置超时机制
        try:
            # 使用异步方法，添加超时控制
            doctor_content, is_end = await asyncio.wait_for(
                workflow.process_response(patient_content),
                timeout=WORKFLOW_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"Workflow execution timed out after {WORKFLOW_TIMEOUT} seconds")
            # 提供一个友好的超时响应
            doctor_content = "抱歉，处理您的请求需要比预期更长的时间。请尝试提供更简洁或更具体的症状描述，或稍后再试。"
            is_end = False
        
        workflow_end_time = time.time()
        logger.info(f"Total Workflow time: {workflow_end_time - workflow_start_time:.2f} seconds")

        # 保存记录
        try:
            db_start_time = time.time()
            if isinstance(doctor_content, str):
                dialogue_db.save_dialogue_record(session_id, workflow.turn_id, patient_content, doctor_content)
            db_end_time = time.time()
            logger.info(f"Respond database save time: {db_end_time - db_start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            # 数据库错误不影响用户响应

        return RespondResponse(
                session_id=session_id,
                doctor_content=doctor_content
            )
    
    except HTTPException as http_ex:
        # 将HTTP异常转换为JSON响应
        logger.warning(f"Input validation error: {http_ex.detail}")
        return JSONResponse(
            status_code=http_ex.status_code,
            content={"detail": http_ex.detail, "session_id": getattr(request, 'session_id', str(uuid.uuid4()))},
        )
    except Exception as e:
        # 捕获所有未处理的异常
        logger.error(f"Unexpected error in respond endpoint: {str(e)}", exc_info=True)
        return RespondResponse(
            session_id=getattr(request, 'session_id', str(uuid.uuid4())),
            doctor_content=DEFAULT_ERROR_RESPONSE
        )