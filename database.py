import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv('.env')

class DatabaseManager:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.table_name = "brand_analysis_requests"
    
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
            # First try to update existing record
            existing = self.supabase.table(self.table_name).select("id").eq("user_id", user_id).eq("session_id", session_id).execute()
            
            if existing.data:
                # Update existing record
                self.supabase.table(self.table_name).update({
                    "question": question,
                    "status": "pending",  # Changed from "running" to "pending"
                    "updated_at": datetime.utcnow().isoformat(),
                    "error_message": None,
                    "results": None
                }).eq("user_id", user_id).eq("session_id", session_id).execute()
                
                return existing.data[0]["id"]
            else:
                # Insert new record
                self.supabase.table(self.table_name).insert({
                    "id": request_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "question": question,
                    "status": "pending"  # Changed from "running" to "pending"
                }).execute()
                
                return request_id
                
        except Exception as e:
            print(f"Error creating request: {e}")
            raise

    def get_existing_request(self, user_id: str, session_id: str):
        """Get existing request by user_id and session_id"""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).eq("session_id", session_id).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            print(f"Error getting existing request: {e}")
            return None
        
    def update_status(self, user_id: str, session_id: str, status: str, error_message: str = None):
        """Update the status of a request"""
        try:
            self.supabase.table(self.table_name).update({
                "status": status,
                "error_message": error_message,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).eq("session_id", session_id).execute()
        except Exception as e:
            print(f"Error updating status: {e}")
    
    def save_results(self, user_id: str, session_id: str, results: Dict[str, Any]):
        """Save the analysis results and mark as completed"""
        try:
            response = self.supabase.table(self.table_name).update({
                "status": "completed",
                "results": results,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).eq("session_id", session_id).execute()
            
        except Exception as e:
            print(f"Error saving results: {e}")
            raise
    
    def get_request_status(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status and results of a request"""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).eq("session_id", session_id).execute()
            
            if response.data:
                return response.data[0]
            return None
            
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