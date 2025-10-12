from typing import List
from datetime import datetime
from pydantic import BaseModel
from .BaseDatabase import BaseDatabase

class DialogueRecord(BaseModel):
    session_id: str
    turn_id: int
    patient_content: str
    doctor_content: str

class DialogueRequest(BaseModel):
    session_id: str
    patient_content: str

class DialogueResponse(BaseModel):
    session_id: str
    doctor_content: str

class DialogueDatabase(BaseDatabase):
    def __init__(self, db_config=None):
        """Initialize the dialogue database."""
        super().__init__(db_config)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize dialogue_records table."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dialogue_records (
                session_id TEXT NOT NULL,
                turn_id INTEGER NOT NULL,
                patient_content TEXT NOT NULL,
                doctor_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, turn_id)
            )
        ''')
        self.conn.commit()

    def save_dialogue_record(self, session_id: str, turn_id: int, patient_content: str, doctor_content: str) -> bool:
        """
        Save a dialogue record to the database.
        """
        try:
            self.cursor.execute('''
                INSERT INTO dialogue_records (session_id, turn_id, patient_content, doctor_content)
                VALUES (%s, %s, %s, %s)
            ''', (session_id, turn_id, patient_content, doctor_content))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving dialogue record: {e}")
            return False
    
    def get_dialogue_list(self, session_id: str) -> List[DialogueRecord]:
        """
        Retrieve all dialogue records for a given session.
        """
        try:
            self.cursor.execute('''
                SELECT session_id, turn_id, patient_content, doctor_content
                FROM dialogue_records
                WHERE session_id = %s
                ORDER BY turn_id ASC
            ''', (session_id,))
            
            records = self.cursor.fetchall()
            
            return [
                DialogueRecord(
                    session_id=record[0],
                    turn_id=record[1],
                    patient_content=record[2],
                    doctor_content=record[3]
                )
                for record in records
            ]
        except Exception as e:
            print(f"Error retrieving dialogue records by session: {e}")
            return []