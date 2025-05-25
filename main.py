import os
import uvicorn
import json
import logging
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.genai import types

from mcp_brand_agent.agent import root_agent
from database import db_manager

# Load environment variables
load_dotenv('.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_NAME = os.environ.get("APP_NAME", "mcp_brand_agent")

ALLOWED_ORIGINS = ["*"]

SESSION_DB_URL = os.environ.get("SESSION_DB_URL")
API_TOKEN = os.environ.get("API_TOKEN")

# Track background tasks
background_tasks: Dict[str, asyncio.Task] = {}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme.")
    if API_TOKEN is None or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    return credentials.credentials

def init_session_service() -> DatabaseSessionService:
    try:
        service = DatabaseSessionService(db_url=SESSION_DB_URL)

        if service is None:
            raise RuntimeError("DatabaseSessionService constructor returned None")

        print(f"DatabaseSessionService initialized successfully. Type: {type(service)}")
        return service
    except Exception as e:
        print(f"Failed to initialize DatabaseSessionService: {e}")
        print(f"Exception type: {type(e)}")
        raise RuntimeError(f"Failed to initialize DatabaseSessionService: {e}")

try:
    session_service = init_session_service()
    print(f"Global session_service initialized: {type(session_service)}")
except Exception as e:
    print(f"CRITICAL: Failed to initialize global session_service: {e}")
    session_service = None

def get_task_key(user_id: str, session_id: str) -> str:
    return f"{user_id}:{session_id}"

async def run_agent_logic(user_id: str, session_id: str, question: str) -> Dict[str, Any]:
    try:
        agent = root_agent
    except Exception as e:
        print(f"Failed to get static agent reference: {e}")
        return {"answerText": "Error: Could not get static agent reference."}

    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    initial_content = types.Content(role="user", parts=[types.Part(text=question)])
    final_response = None

    try:
        events = runner.run_async(
            user_id=user_id, session_id=session_id, new_message=initial_content
        )

        async for event in events:
            if event.is_final_response():
                if (
                    event.content is None
                    or not hasattr(event.content, "parts")
                    or not event.content.parts
                ):
                    print("Warning: Final response event has no content or parts")
                    continue

                response_text = event.content.parts[0].text
                try:
                    final_response = json.loads(response_text)
                except json.JSONDecodeError:
                    final_response = {"answerText": response_text}

    except Exception as e:
        print(f"An error occurred during agent execution for session {session_id}: {e}")
        if final_response is None:
            final_response = {
                "answerText": "An internal error occurred during agent execution."
            }

    return final_response

async def get_or_create_session(user_id: str, session_id: str) -> Any:
    try:
        if session_service is None:
            print("ERROR: session_service is None!")
            raise RuntimeError("Session service not initialized")

        print(f"DEBUG: session_service type: {type(session_service)}")
        print(
            f"DEBUG: Attempting to get session for user_id={user_id}, session_id={session_id}"
        )

        current_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        if not current_session:
            print(
                f"Session not found for user {user_id}, session {session_id}. Creating new session."
            )

            current_session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )

        return current_session

    except Exception as e:
        print(f"Error during session lookup/creation for session {session_id}: {e}")
        raise

class QueryRequest(BaseModel):
    userId: str
    sessionId: str
    question: str

async def process_brand_analysis_background(user_id: str, session_id: str, question: str):
    task_key = get_task_key(user_id, session_id)
    
    try:
        db_manager.update_status(user_id, session_id, "processing")
        
        await get_or_create_session(user_id, session_id)

        await run_agent_logic(user_id, session_id, question)

        updated_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        analysis_results_twitter = updated_session.state.get("final_twitter_results", {})
        analysis_results_linkedin = updated_session.state.get("final_linkedin_results", {})
        analysis_results_reddit = updated_session.state.get("final_reddit_results", {})
        analysis_results_news = updated_session.state.get("final_news_results", {})

        def parse_result(result_data):
            if isinstance(result_data, str):
                try:
                    return json.loads(result_data)
                except json.JSONDecodeError:
                    return {"raw_data": result_data}
            return result_data if result_data else {}

        analysis_results_twitter = parse_result(analysis_results_twitter)
        analysis_results_linkedin = parse_result(analysis_results_linkedin)
        analysis_results_reddit = parse_result(analysis_results_reddit)
        analysis_results_news = parse_result(analysis_results_news)

        response_data = {
            "userId": user_id,
            "sessionId": session_id,
            "brand_name": question.split()[0] if question else "Unknown",
            "analysis_results_twitter": analysis_results_twitter,
            "analysis_results_linkedin": analysis_results_linkedin,
            "analysis_results_reddit": analysis_results_reddit,
            "analysis_results_news": analysis_results_news
        }

        db_manager.save_results(user_id, session_id, response_data)
        
        logger.info(f"Background processing completed for user {user_id}, session {session_id}")

    except Exception as e:
        logger.error(f"Background processing failed for user {user_id}, session {session_id}: {e}")
        db_manager.update_status(user_id, session_id, "failed", str(e))
    finally:
        # Clean up the task reference
        background_tasks.pop(task_key, None)

@app.post("/query")
async def query_endpoint(request_data: QueryRequest, token: str = Depends(verify_bearer_token)):
    try:
        task_key = get_task_key(request_data.userId, request_data.sessionId)
        
        # Check if already processing
        if task_key in background_tasks and not background_tasks[task_key].done():
            return {
                "message": "Brand analysis is already being processed for this session",
                "userId": request_data.userId,
                "sessionId": request_data.sessionId,
                "status": "processing",
                "statusEndpoint": f"/status/{request_data.userId}/{request_data.sessionId}"
            }
        
        request_id = db_manager.create_request(
            request_data.userId, 
            request_data.sessionId, 
            request_data.question
        )
        
        # Create background task using asyncio
        task = asyncio.create_task(
            process_brand_analysis_background(
                request_data.userId,
                request_data.sessionId,
                request_data.question
            )
        )
        background_tasks[task_key] = task
        
        # Return immediately
        return {
            "message": "Brand analysis request received and is being processed",
            "userId": request_data.userId,
            "sessionId": request_data.sessionId,
            "requestId": request_id,
            "status": "processing",
            "statusEndpoint": f"/status/{request_data.userId}/{request_data.sessionId}"
        }

    except ValueError as e:
        logger.error(f"Validation error in query_endpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled exception in query_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/status/{user_id}/{session_id}")
async def get_status(user_id: str, session_id: str, token: str = Depends(verify_bearer_token)):
    try:
        status_data = db_manager.get_request_status(user_id, session_id)
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Request not found")
        
        response = {
            "userId": user_id,
            "sessionId": session_id,
            "status": status_data["status"],
            "createdAt": status_data["created_at"],
            "updatedAt": status_data["updated_at"]
        }
        
        if status_data["status"] == "failed" and status_data.get("error_message"):
            response["errorMessage"] = status_data["error_message"]
        
        if status_data["status"] == "completed" and status_data.get("results"):
            response["results"] = status_data["results"]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for {user_id}/{session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    active_tasks = sum(1 for task in background_tasks.values() if not task.done())
    return {
        "status": "healthy",
        "active_background_tasks": active_tasks,
        "total_background_tasks": len(background_tasks),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)