from typing import Dict, Optional, Any
from pydantic import BaseModel
from service.Model.base import BaseDatabase
from datetime import datetime

class ReportResponse(BaseModel):
    """
    报告请求数据模型
    """
    session_id: str
    chief_complaint: str      # 主诉
    hpi: str                  # 现病史
    past_history: str         # 既往史
    triage_result: str        # 分诊结果

class ReportModel(BaseDatabase):
    def __init__(self, db_config=None):
        """初始化报告数据库模型。"""
        super().__init__(db_config)
        self._init_tables()

    def _init_tables(self):
        """
        初始化病历报告表。
        如果表不存在，则创建该表。
        """
        query = """
        CREATE TABLE IF NOT EXISTS medical_reports (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL UNIQUE,
            chief_complaint TEXT,
            hpi TEXT,
            past_history TEXT,
            triage_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.cursor.execute(query)

    def save_report(self, session_id: str, chief_complaint: str, hpi: str, past_history: str, triage_result: str):
        """
        保存或更新病历报告到数据库。
        
        参数:
            session_id: 会话ID
            chief_complaint: 主诉
            hpi: 现病史
            past_history: 既往史
            triage_result: 分诊结果
        """
        # 使用 UPSERT (INSERT ... ON CONFLICT UPDATE) 逻辑
        # 如果 session_id 已存在，则更新记录；否则插入新记录
        query = """
        INSERT INTO medical_reports (session_id, chief_complaint, hpi, past_history, triage_result, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (session_id) 
        DO UPDATE SET 
            chief_complaint = EXCLUDED.chief_complaint,
            hpi = EXCLUDED.hpi,
            past_history = EXCLUDED.past_history,
            triage_result = EXCLUDED.triage_result,
            created_at = EXCLUDED.created_at;
        """
        self.cursor.execute(query, (session_id, chief_complaint, hpi, past_history, triage_result, datetime.now()))

    def get_report_by_session(self, session_id: str):
        """
        根据 session_id 获取病历报告。
        
        参数:
            session_id: 会话ID
            
        返回:
            dict: 包含报告详情的字典，如果未找到则返回 None
        """
        query = """
        SELECT chief_complaint, hpi, past_history, triage_result, created_at 
        FROM medical_reports 
        WHERE session_id = %s
        """
        self.cursor.execute(query, (session_id,))
        result = self.cursor.fetchone()
        
        if result:
            return {
                "chief_complaint": result[0],
                "hpi": result[1],
                "past_history": result[2],
                "triage_result": result[3],
                "created_at": result[4]
            }
        return None