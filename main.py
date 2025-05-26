import os
import uvicorn
import json
import logging
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# session_service = InMemorySessionService()


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


async def get_or_create_session(user_id: str, session_id: str) -> Any:
    """
    Retrieves an existing session or creates a new one if it doesn't exist.
    """
    try:
        if session_service is None:
            print("ERROR: session_service is None!")
            raise RuntimeError("Session service not initialized")

        print(f"DEBUG: Attempting to get session for user_id={user_id}, session_id={session_id}")

        current_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        if not current_session:
            print(f"Session not found for user {user_id}, session {session_id}. Creating new session.")
            current_session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )

        # Verify session was created properly
        if not current_session:
            raise RuntimeError(f"Failed to create session for user {user_id}, session {session_id}")

        return current_session

    except Exception as e:
        print(f"Error during session lookup/creation for session {session_id}: {e}")
        raise


class QueryRequest(BaseModel):
    userId: str
    sessionId: str
    question: str


@app.post("/query")
async def query_endpoint(request_data: QueryRequest):
    try:
        # Check if analysis already exists
        existing_request = db_manager.get_existing_request(
            request_data.userId, 
            request_data.sessionId
        )
        
        if existing_request:
            if existing_request['status'] == 'completed':
                return existing_request['results']
            elif existing_request['status'] in ['pending', 'running']:
                return {"message": "Analysis already in progress"}
        
        # Create database entry with 'pending' status
        db_manager.create_request(
            request_data.userId, 
            request_data.sessionId, 
            request_data.question
        )
        
        # Update status to 'running' when analysis starts
        db_manager.update_status(request_data.userId, request_data.sessionId, "running")
        
        # Get or create session FIRST
        await get_or_create_session(
            request_data.userId,
            request_data.sessionId
        )

        # Run the agent logic BEFORE accessing session state
        await run_agent_logic(
            request_data.userId,
            request_data.sessionId,
            request_data.question
        )

        # NOW get updated session after agent execution
        updated_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=request_data.userId,
            session_id=request_data.sessionId,
        )

        # Check if session exists and has state
        if not updated_session or not hasattr(updated_session, 'state') or not updated_session.state:
            raise ValueError("Session state is empty after agent execution")

        analysis_results_twitter = updated_session.state.get("final_twitter_results", {})
        analysis_results_linkedin = updated_session.state.get("final_linkedin_results", {})
        analysis_results_reddit = updated_session.state.get("final_reddit_results", {})
        analysis_results_news = updated_session.state.get("final_news_results", {})

        # Parse JSON strings if needed
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
            "userId": request_data.userId,
            "sessionId": request_data.sessionId,
            "analysis_results_twitter": analysis_results_twitter,
            "analysis_results_linkedin": analysis_results_linkedin,
            "analysis_results_reddit": analysis_results_reddit,
            "analysis_results_news": analysis_results_news
        }

        # Update status to 'completed' when done
        db_manager.update_status(request_data.userId, request_data.sessionId, "completed")
        db_manager.save_results(request_data.userId, request_data.sessionId, response_data)

        return response_data

    except ValueError as e:
        db_manager.update_status(request_data.userId, request_data.sessionId, "failed", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled exception in query_endpoint: {e}")
        db_manager.update_status(request_data.userId, request_data.sessionId, "failed", "Internal server error.")
        raise HTTPException(status_code=500, detail="Internal server error.")


if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)