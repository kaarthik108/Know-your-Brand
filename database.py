import os
import json
import uuid
import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv('.env')

class DatabaseManager:
    def __init__(self):
        # Parse the PostgreSQL URL from SESSION_DB_URL
        db_url = os.getenv("SESSION_DB_URL")
        if not db_url:
            raise ValueError("SESSION_DB_URL environment variable is required")
        
        self.db_url = db_url
        self.table_name = "brand_analysis_requests"
        self._init_table()
    
    def _get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.db_url)
    
    def _init_table(self):
        """Initialize the required table if it doesn't exist"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            user_id VARCHAR(255) NOT NULL,
                            session_id VARCHAR(255) NOT NULL,
                            question VARCHAR(255) NOT NULL,
                            status VARCHAR(50) NOT NULL DEFAULT 'pending',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            error_message TEXT,
                            results JSONB,
                            UNIQUE(user_id, session_id)
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_brand_analysis_user_session 
                        ON {self.table_name}(user_id, session_id);
                        
                        CREATE INDEX IF NOT EXISTS idx_brand_analysis_status 
                        ON {self.table_name}(status);
                    """)
                    conn.commit()
        except Exception as e:
            print(f"Warning: Could not initialize database table: {e}")
            # Don't raise here - let the app continue
    
    def init_tables(self):
        """Initialize the required tables if they don't exist"""
        # Note: With Supabase, you typically create tables through the dashboard or SQL editor
        # This method is kept for compatibility but tables should be created in Supabase dashboard
        print("Database tables should be created in Supabase dashboard")
        print("Table schema:")
        print("""
        CREATE TABLE IF NOT EXISTS brand_analysis_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            question VARCHAR(255) NOT NULL,
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
        """)
    
    def create_request(self, user_id: str, session_id: str, question: str) -> str:
        """Create a new brand analysis request and return the request ID"""
        request_id = str(uuid.uuid4())
        
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # First try to update existing record
                    cur.execute(
                        f"SELECT id FROM {self.table_name} WHERE user_id = %s AND session_id = %s",
                        (user_id, session_id)
                    )
                    existing = cur.fetchone()
                    
                    if existing:
                        # Update existing record
                        cur.execute(f"""
                            UPDATE {self.table_name} 
                            SET question = %s, status = 'pending', updated_at = CURRENT_TIMESTAMP, 
                                error_message = NULL, results = NULL
                            WHERE user_id = %s AND session_id = %s
                        """, (question, user_id, session_id))
                        conn.commit()
                        return str(existing["id"])
                    else:
                        # Insert new record
                        cur.execute(f"""
                            INSERT INTO {self.table_name} (id, user_id, session_id, question, status)
                            VALUES (%s, %s, %s, %s, 'pending')
                        """, (request_id, user_id, session_id, question))
                        conn.commit()
                        return request_id
                        
        except Exception as e:
            print(f"Error creating request: {e}")
            raise

    def get_existing_request(self, user_id: str, session_id: str):
        """Get existing request by user_id and session_id"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        f"SELECT * FROM {self.table_name} WHERE user_id = %s AND session_id = %s",
                        (user_id, session_id)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            print(f"Error getting existing request: {e}")
            return None
        
    def update_status(self, user_id: str, session_id: str, status: str, error_message: str = None):
        """Update the status of a request"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE {self.table_name} 
                        SET status = %s, error_message = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND session_id = %s
                    """, (status, error_message, user_id, session_id))
                    conn.commit()
        except Exception as e:
            print(f"Error updating status: {e}")
    
    def save_results(self, user_id: str, session_id: str, results: Dict[str, Any]):
        """Save the analysis results and mark as completed"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE {self.table_name} 
                        SET status = 'completed', results = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND session_id = %s
                    """, (json.dumps(results), user_id, session_id))
                    conn.commit()
                    
        except Exception as e:
            print(f"Error saving results: {e}")
            raise
    
    def get_request_status(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status and results of a request"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        f"SELECT * FROM {self.table_name} WHERE user_id = %s AND session_id = %s",
                        (user_id, session_id)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            print(f"Error getting request status: {e}")
            raise
    
    def cleanup_old_requests(self, days: int = 7):
        """Clean up old completed/failed requests"""
        try:
            # Calculate cutoff date
            from datetime import timedelta
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get records to delete first (to count them)
            old_records = self.supabase.table(self.table_name).select("id").lt("updated_at", cutoff_date).in_("status", ["completed", "failed"]).execute()
            
            if old_records.data:
                # Delete the records
                ids_to_delete = [record["id"] for record in old_records.data]
                response = self.supabase.table(self.table_name).delete().in_("id", ids_to_delete).execute()
                
                deleted_count = len(old_records.data)
                print(f"Cleaned up {deleted_count} old requests")
                return deleted_count
            else:
                print("No old requests to clean up")
                return 0
                
        except Exception as e:
            print(f"Error cleaning up old requests: {e}")
            raise

db_manager = DatabaseManager() 