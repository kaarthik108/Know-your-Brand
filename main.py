import os
import uvicorn
import asyncio
import json
import logging
from typing import Any, Dict, Optional
import threading

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mcp_brand_agent.agent import root_agent
from database import db_manager

# Load environment variables
load_dotenv('.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_NAME = os.environ.get("APP_NAME", "mcp_brand_agent")

ALLOWED_ORIGINS = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
# @app.on_event("startup")
# async def startup_event():
#     try:
#         db_manager.init_tables()
#         logger.info("Database initialized successfully")
#     except Exception as e:
#         logger.error(f"Failed to initialize database: {e}")
#         raise


# def init_session_service() -> DatabaseSessionService:
#     try:
#         service = DatabaseSessionService(db_url=SESSION_DB_URL)

#         if service is None:
#             raise RuntimeError("DatabaseSessionService constructor returned None")

#         print(f"DatabaseSessionService initialized successfully. Type: {type(service)}")
#         return service
#     except Exception as e:
#         print(f"Failed to initialize DatabaseSessionService: {e}")
#         print(f"Exception type: {type(e)}")
#         raise RuntimeError(f"Failed to initialize DatabaseSessionService: {e}")


# try:
#     session_service = init_session_service()
#     print(f"Global session_service initialized: {type(session_service)}")
# except Exception as e:
#     print(f"CRITICAL: Failed to initialize global session_service: {e}")
#     session_service = None

session_service = InMemorySessionService()


async def run_agent_logic_background(
    user_id: str, session_id: str, question: str, brand_name: str
):
    """
    Background task to run the agent logic and update database status
    """
    try:
        # Update status to running
        db_manager.update_status(user_id, session_id, "running")
        
        # Run the actual agent logic
        result = await run_agent_logic(user_id, session_id, question)
        
        # Get updated session after agent execution
        updated_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        
        analysis_results_twitter = updated_session.state.get("final_twitter_results", {})
        analysis_results_linkedin = updated_session.state.get("final_linkedin_results", {})
        analysis_results_reddit = updated_session.state.get("final_reddit_results", {})
        analysis_results_news = updated_session.state.get("final_news_results", {})
        
        # Parse JSON strings if needed
        if isinstance(analysis_results_twitter, str):
            try:
                analysis_results_twitter = json.loads(analysis_results_twitter)
            except json.JSONDecodeError:
                analysis_results_twitter = {"analysis_results_twitter": analysis_results_twitter}
                
        if isinstance(analysis_results_linkedin, str):
            try:
                analysis_results_linkedin = json.loads(analysis_results_linkedin)
            except json.JSONDecodeError:
                analysis_results_linkedin = {"analysis_results_linkedin": analysis_results_linkedin}
                
        if isinstance(analysis_results_reddit, str):
            try:
                analysis_results_reddit = json.loads(analysis_results_reddit)
            except json.JSONDecodeError:
                analysis_results_reddit = {"analysis_results_reddit": analysis_results_reddit}
                
        if isinstance(analysis_results_news, str):
            try:
                analysis_results_news = json.loads(analysis_results_news)
            except json.JSONDecodeError:
                analysis_results_news = {"analysis_results_news": analysis_results_news}

        response_data = {
            "userId": user_id,
            "sessionId": session_id,
            "brand_name": brand_name,
            "analysis_results_twitter": analysis_results_twitter if analysis_results_twitter else {},
            "analysis_results_linkedin": analysis_results_linkedin if analysis_results_linkedin else {},
            "analysis_results_reddit": analysis_results_reddit if analysis_results_reddit else {},
            "analysis_results_news": analysis_results_news if analysis_results_news else {}
        }
        
        # Save results to database
        db_manager.save_results(user_id, session_id, response_data)
        logger.info(f"Analysis completed successfully for user {user_id}, session {session_id}")
        
    except Exception as e:
        logger.error(f"Error in background analysis for user {user_id}, session {session_id}: {e}")
        db_manager.update_status(user_id, session_id, "failed", str(e))


async def run_agent_logic(
    user_id: str, session_id: str, question: str
) -> Dict[str, Any]:
    """
    Runs the agent logic asynchronously, using pre-updated session state.

    Args:
        user_id: Unique identifier for the user
        session_id: Unique identifier for the session
        question: The user's question or input

    Returns:
        Dictionary containing the agent's response
    """
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


async def get_or_create_session(
    user_id: str, session_id: str
) -> Any:
    """
    Retrieves an existing session or creates a new one if it doesn't exist.

    Args:
        user_id: Unique identifier for the user
        session_id: Unique identifier for the session

    Returns:
        Session object
    """
    try:
        # Debug: Check if session_service is None
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
    brand_name: str = None


@app.post("/query")
async def query_endpoint(request_data: QueryRequest, background_tasks: BackgroundTasks):
    try:
        # Extract brand name from question if not provided
        brand_name = request_data.brand_name or request_data.question.split()[0] if request_data.question else "Unknown"
        
        # Create database entry and get request ID
        request_id = db_manager.create_request(
            request_data.userId, 
            request_data.sessionId, 
            brand_name
        )
        
        # Get or create session
        await get_or_create_session(
            request_data.userId,
            request_data.sessionId
        )
        
        # Start background task for analysis
        background_tasks.add_task(
            run_agent_logic_background,
            request_data.userId,
            request_data.sessionId,
            request_data.question,
            brand_name
        )
        
        # Return immediate response with request ID and status
        return {
            "request_id": request_id,
            "userId": request_data.userId,
            "sessionId": request_data.sessionId,
            "brand_name": brand_name,
            "status": "running",
            "message": "Analysis started. Use the status endpoint to check progress."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled exception in query_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.get("/status/{user_id}/{session_id}")
async def get_status(user_id: str, session_id: str):
    """
    Get the current status of a brand analysis request
    """
    try:
        status_data = db_manager.get_request_status(user_id, session_id)
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Request not found")
        
        response = {
            "request_id": status_data["id"],
            "userId": user_id,
            "sessionId": session_id,
            "brand_name": status_data["brand_name"],
            "status": status_data["status"],
            "created_at": status_data["created_at"].isoformat() if status_data["created_at"] else None,
            "updated_at": status_data["updated_at"].isoformat() if status_data["updated_at"] else None,
        }
        
        if status_data["status"] == "failed" and status_data["error_message"]:
            response["error_message"] = status_data["error_message"]
        
        if status_data["status"] == "completed" and status_data["results"]:
            response["results"] = status_data["results"]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for user {user_id}, session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/cleanup")
async def cleanup_old_requests(days: int = 7):
    """
    Clean up old completed/failed requests (admin endpoint)
    """
    try:
        deleted_count = db_manager.cleanup_old_requests(days)
        return {
            "message": f"Cleaned up {deleted_count} old requests",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)