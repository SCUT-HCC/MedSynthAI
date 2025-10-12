import psycopg2
import os
from datetime import datetime

class BaseDatabase:
    def __init__(self, db_config=None):
        """Initialize the database connection."""
        # 默认PostgreSQL连接配置
        default_config = {
            'host': '110.42.53.85',
            'port': 5432,
            'dbname': 'MedSynthAI',
            'user': 'MedSynthAI',
            'password': 'SecurePass123'
        }
        
        # 使用提供的配置或默认配置
        self.db_config = db_config or default_config
        
        # 连接到PostgreSQL数据库
        self.conn = psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            dbname=self.db_config['dbname'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )
        
        # 设置自动提交
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()
    
    def _init_tables(self):
        """Initialize database tables. Should be implemented by child classes."""
        raise NotImplementedError
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()