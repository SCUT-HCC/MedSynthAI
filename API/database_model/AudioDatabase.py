from typing import Optional
from datetime import datetime
from .BaseDatabase import BaseDatabase

class AudioDatabase(BaseDatabase):
    def __init__(self, db_config=None):
        """Initialize the audio database."""
        super().__init__(db_config)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize audio_records table."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS audio_records (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                upload_time TIMESTAMP NOT NULL,
                transcription TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def save_audio_record(self, id: str, filename: str, upload_time: datetime, transcription: Optional[str] = None) -> bool:
        """
        Save an audio record to the database.
        
        Args:
            id: Unique identifier for the audio record
            filename: Name of the audio file
            upload_time: Time when the audio was uploaded
            transcription: Transcription of the audio (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
                INSERT INTO audio_records (id, filename, upload_time, transcription)
                VALUES (%s, %s, %s, %s)
            ''', (id, filename, upload_time, transcription))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving audio record: {e}")
            return False
    
    def get_audio_record(self, id: str) -> Optional[dict]:
        """
        Retrieve an audio record by ID.
        
        Args:
            id: Unique identifier for the audio record
            
        Returns:
            Optional[dict]: Record data if found, None otherwise
        """
        try:
            self.cursor.execute('''
                SELECT id, filename, upload_time, transcription, created_at
                FROM audio_records
                WHERE id = %s
            ''', (id,))
            
            record = self.cursor.fetchone()
            if record:
                return {
                    'id': record[0],
                    'filename': record[1],
                    'upload_time': datetime.fromisoformat(record[2]),
                    'transcription': record[3],
                    'created_at': datetime.fromisoformat(record[4])
                }
            return None
        except Exception as e:
            print(f"Error retrieving audio record: {e}")
            return None 