from typing import Dict, Optional, Any, List
from pydantic import BaseModel
from service.Model.base import BaseDatabase
from datetime import datetime

class ChatRequest(BaseModel):
    """
    聊天请求数据模型
    """
    session_id: str = ""      # 会话ID，空字符串表示新会话
    patient_content: str      # 前端输入的患者回答内容

class ChatResponse(BaseModel):
    """
    聊天响应数据模型
    """
    session_id: str
    worker_inquiry: str       # 医生的回复或追问
    is_completed: bool        # 问诊流程是否已结束

class ChatModel(BaseDatabase):
    def __init__(self, db_config=None):
        """初始化聊天数据库模型。"""
        super().__init__(db_config)
        self._init_tables()

    def _init_tables(self):
        """
        初始化聊天记录表。
        如果表不存在，则创建该表。
        """
        query = """
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            content TEXT,
            step_num INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.cursor.execute(query)

    def save_record(self, session_id: str, role: str, content: str, step_num: int):
        """
        保存单条聊天记录到数据库。
        
        参数:
            session_id: 会话ID
            role: 角色标识 ('doctor' 或 'patient')
            content: 聊天文本内容
            step_num: 当前对话轮次
        """
        query = """
        INSERT INTO chat_history (session_id, role, content, step_num, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (session_id, role, content, step_num, datetime.now()))

    def get_history_by_session(self, session_id: str):
        """
        根据 session_id 获取完整的历史对话记录。
        
        参数:
            session_id: 会话ID
            
        返回:
            list: 包含 (role, content, step_num, created_at) 的元组列表，按时间正序排列。
        """
        query = """
        SELECT role, content, step_num, created_at 
        FROM chat_history 
        WHERE session_id = %s 
        ORDER BY created_at ASC
        """
        self.cursor.execute(query, (session_id,))
        return self.cursor.fetchall()