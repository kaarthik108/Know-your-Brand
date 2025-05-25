import psycopg2
from psycopg2.extras import RealDictCursor
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.connection_params = {
            'user': os.getenv("user"),
            'password': os.getenv("password"),
            'host': os.getenv("host"),
            'port': os.getenv("port"),
            'dbname': os.getenv("dbname")
        }
    
    def get_connection(self):
        return psycopg2.connect(**self.connection_params)
    
    def init_tables(self):
        """Initialize the required tables if they don't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS brand_analysis_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            brand_name VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT,
            results JSONB,
            UNIQUE(user_id, session_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_brand_analysis_user_session 
        ON brand_analysis_requests(user_id, session_id);
        
        CREATE INDEX IF NOT EXISTS idx_brand_analysis_status 
        ON brand_analysis_requests(status);
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_table_sql)
                    conn.commit()
                    print("Database tables initialized successfully")
        except Exception as e:
            print(f"Error initializing tables: {e}")
            raise
    
    def create_request(self, user_id: str, session_id: str, brand_name: str) -> str:
        """Create a new brand analysis request and return the request ID"""
        request_id = str(uuid.uuid4())
        
        insert_sql = """
        INSERT INTO brand_analysis_requests (id, user_id, session_id, brand_name, status)
        VALUES (%s, %s, %s, %s, 'running')
        ON CONFLICT (user_id, session_id) 
        DO UPDATE SET 
            brand_name = EXCLUDED.brand_name,
            status = 'running',
            updated_at = CURRENT_TIMESTAMP,
            error_message = NULL,
            results = NULL
        RETURNING id;
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(insert_sql, (request_id, user_id, session_id, brand_name))
                    result = cursor.fetchone()
                    conn.commit()
                    return result[0] if result else request_id
        except Exception as e:
            print(f"Error creating request: {e}")
            raise
    
    def update_status(self, user_id: str, session_id: str, status: str, error_message: str = None):
        """Update the status of a request"""
        update_sql = """
        UPDATE brand_analysis_requests 
        SET status = %s, updated_at = CURRENT_TIMESTAMP, error_message = %s
        WHERE user_id = %s AND session_id = %s
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(update_sql, (status, error_message, user_id, session_id))
                    conn.commit()
        except Exception as e:
            print(f"Error updating status: {e}")
            raise
    
    def save_results(self, user_id: str, session_id: str, results: Dict[str, Any]):
        """Save the analysis results and mark as completed"""
        update_sql = """
        UPDATE brand_analysis_requests 
        SET status = 'completed', results = %s, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s AND session_id = %s
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(update_sql, (json.dumps(results), user_id, session_id))
                    conn.commit()
        except Exception as e:
            print(f"Error saving results: {e}")
            raise
    
    def get_request_status(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status and results of a request"""
        select_sql = """
        SELECT id, status, created_at, updated_at, error_message, results, brand_name
        FROM brand_analysis_requests 
        WHERE user_id = %s AND session_id = %s
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(select_sql, (user_id, session_id))
                    result = cursor.fetchone()
                    if result:
                        return dict(result)
                    return None
        except Exception as e:
            print(f"Error getting request status: {e}")
            raise
    
    def cleanup_old_requests(self, days: int = 7):
        """Clean up old completed/failed requests"""
        cleanup_sql = """
        DELETE FROM brand_analysis_requests 
        WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
        AND status IN ('completed', 'failed')
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(cleanup_sql, (days,))
                    deleted_count = cursor.rowcount
                    conn.commit()
                    print(f"Cleaned up {deleted_count} old requests")
                    return deleted_count
        except Exception as e:
            print(f"Error cleaning up old requests: {e}")
            raise

db_manager = DatabaseManager() 