import os
import psycopg2
from datetime import datetime
from typing import List
from .BaseDatabase import BaseDatabase
from pydantic import BaseModel

class TriageRecord(BaseModel):
    session_id: str
    turn_id: int
    hpi: str

class TriageDatabase(BaseDatabase):
    def __init__(self, db_config=None):
        """Initialize the database connection and create tables if they don't exist."""
        super().__init__(db_config)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize triage_records table."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS triage_records (
                session_id TEXT NOT NULL,
                turn_id INTEGER NOT NULL,
                hpi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, turn_id)
            )
        ''')
        self.conn.commit()
    
    def save_triage_record(self, session_id: str, turn_id: int, hpi: str) -> bool:
        """
        Save a triage record to the database.
        """
        try:
            self.cursor.execute('''
                INSERT INTO triage_records (session_id, turn_id, hpi)
                VALUES (%s, %s, %s)
            ''', (session_id, turn_id, hpi))
            self.conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Error saving triage record: {e}")
            return False
    
    def get_triage_record(self, session_id: str, turn_id: int) -> TriageRecord:
        """
        Retrieve a triage record by session_id and turn_id.
        """
        try:
            self.cursor.execute('''
                SELECT session_id, turn_id, hpi
                FROM triage_records
                WHERE session_id = %s AND turn_id = %s
            ''', (session_id, turn_id))
            
            record = self.cursor.fetchone()
            if record:
                return TriageRecord(
                    session_id=record[0],
                    turn_id=record[1],
                    hpi=record[2],
                )
            return None
        except psycopg2.Error as e:
            print(f"Error retrieving triage record: {e}")
            return None
    
    def get_triage_list(self, session_id: str) -> List[TriageRecord]:
        """
        Retrieve all triage records for a given session.
        """
        try:
            self.cursor.execute('''
                SELECT session_id, turn_id, hpi
                FROM triage_records
                WHERE session_id = %s
                ORDER BY turn_id ASC
            ''', (session_id,))

            records = self.cursor.fetchall()

            return [TriageRecord(
                session_id=record[0],
                turn_id=record[1],
                hpi=record[2],
            ) for record in records]

        except psycopg2.Error as e:
            print(f"Error retrieving session records: {e}")
            return []