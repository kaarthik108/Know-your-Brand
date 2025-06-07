import os
from typing import Optional
from google.adk.sessions import DatabaseSessionService, Session
import logging
logger = logging.getLogger(__name__)

APP_NAME = os.environ.get("APP_NAME", "mcp_brand_agent")
class AsyncSessionService:
    """Async wrapper for ADK session service"""
    
    def __init__(self):
        self._session_service: Optional[DatabaseSessionService] = None
    
    async def get_session_service(self) -> DatabaseSessionService:
        """Get or create session service instance"""
        if self._session_service is None:
            try:
                self._session_service = DatabaseSessionService(db_url=os.getenv("SESSION_DB_URL"))
                logger.info("DatabaseSessionService initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize DatabaseSessionService: {e}")
                raise RuntimeError(f"Failed to initialize DatabaseSessionService: {e}")
        
        return self._session_service
    
    async def get_or_create_session(
        self,
        user_id: str,
        session_id: str,
    ) -> Session:
        """Get existing session or create new one"""
        try:
            service = await self.get_session_service()
            
            current_session = await service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
            
            if not current_session:
                logger.info(f"Creating new session for user {user_id}, session {session_id}")
                
                current_session = await service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                )
            
            return current_session
            
        except Exception as e:
            logger.error(f"Error during session lookup/creation for session {session_id}: {e}")
            raise
    
    async def get_session(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[Session]:
        """Get existing session"""
        try:
            service = await self.get_session_service()
            return await service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise


session_service = AsyncSessionService() 