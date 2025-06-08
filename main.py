import os
import uvicorn
import json
import logging
import asyncio
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from database import db_manager
from mcp_brand_agent.agent import root_agent
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

async def init_session_service() -> DatabaseSessionService:
    try:
        service = DatabaseSessionService(db_url=SESSION_DB_URL)
        print(f"DatabaseSessionService initialized with URL: {SESSION_DB_URL}")
        return service
    except Exception as e:
        print(f"Failed to initialize ADK components: {e}")
        raise RuntimeError(f"Failed to initialize ADK components: {e}")

# Global session service will be initialized on first use
session_service = None

async def get_session_service():
    global session_service
    if session_service is None:
        session_service = await init_session_service()
        print(f"Global session_service initialized: {type(session_service)}")
    return session_service

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

    service = await get_session_service()
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=service)

    initial_content = types.Content(role="user", parts=[types.Part(text=f"user_input: {question}")])
    final_response = None

    try:
        # Add timeout wrapper for the entire agent execution
        async def execute_agent():
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
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        return {"answerText": response_text}
            
            return None
        
        # Execute with timeout
        final_response = await asyncio.wait_for(execute_agent(), timeout=60.0)
        
        if final_response is None:
            final_response = {"answerText": "No response received from agent"}

    except asyncio.TimeoutError:
        print(f"Agent execution timed out after 60 seconds for session {session_id}")
        final_response = {
            "answerText": "Agent execution timed out. Please try again later."
        }
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
        service = await get_session_service()
        if service is None:
            print("ERROR: session_service is None!")
            raise RuntimeError("Session service not initialized")

        print(f"DEBUG: Attempting to get session for user_id={user_id}, session_id={session_id}")

        current_session = await service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        if not current_session:
            print(f"Session not found for user {user_id}, session {session_id}. Creating new session.")
            current_session = await service.create_session(
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
        existing_request = await db_manager.get_existing_request(
            request_data.userId, 
            request_data.sessionId
        )
        
        if existing_request:
            if existing_request['status'] == 'completed':
                return existing_request['results']
            elif existing_request['status'] in ['pending', 'running']:
                return {"message": "Analysis already in progress"}
        
        # Create database entry with 'pending' status
        await db_manager.create_request(
            request_data.userId, 
            request_data.sessionId, 
            request_data.question
        )
        
        # Update status to 'running' when analysis starts
        await db_manager.update_status(request_data.userId, request_data.sessionId, "running")
        
        # Get or create session FIRST
        await get_or_create_session(
            request_data.userId,
            request_data.sessionId
        )

        # Run the agent logic BEFORE accessing session state
        try:
            agent_response = await run_agent_logic(
                request_data.userId,
                request_data.sessionId,
                request_data.question
            )
            print(f"Agent response: {agent_response}")
            
            # Check if agent execution failed
            if agent_response.get("answerText") == "An internal error occurred during agent execution.":
                print("Agent execution failed, updating status")
                await db_manager.update_status(request_data.userId, request_data.sessionId, "failed", "Agent execution failed due to timeout")
                raise HTTPException(status_code=500, detail="Agent execution failed due to timeout")
                
        except Exception as agent_error:
            print(f"Agent execution failed: {agent_error}")
            await db_manager.update_status(request_data.userId, request_data.sessionId, "failed", str(agent_error))
            raise HTTPException(status_code=500, detail="Agent execution failed")

        # NOW get updated session after agent execution
        service = await get_session_service()
        updated_session = await service.get_session(
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
        await db_manager.update_status(request_data.userId, request_data.sessionId, "completed")
        await db_manager.save_results(request_data.userId, request_data.sessionId, response_data)

        return response_data

    except ValueError as e:
        await db_manager.update_status(request_data.userId, request_data.sessionId, "failed", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unhandled exception in query_endpoint: {e}")
        await db_manager.update_status(request_data.userId, request_data.sessionId, "failed", "Internal server error.")
        raise HTTPException(status_code=500, detail="Internal server error.")


if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)