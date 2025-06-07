import os
import uvicorn
import json
import logging
import asyncio
from typing import Any, Dict, AsyncGenerator
from contextlib import asynccontextmanager

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

session_service = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    global session_service
    
    logger.info(f"Starting {APP_NAME} application")
    
    try:
        if SESSION_DB_URL:
            session_service = DatabaseSessionService(db_url=SESSION_DB_URL)
            logger.info(f"DatabaseSessionService initialized with URL: {SESSION_DB_URL}")
        else:
            session_service = InMemorySessionService()
            logger.info("InMemorySessionService initialized (no SESSION_DB_URL provided)")
            
        db_manager.init_tables()
        logger.info("Database tables initialized")
        
        try:
            agent_test = root_agent
            logger.info("Agent successfully imported and accessible")
            
            # Test MCP token availability
            mcp_token = os.getenv("MCP_TOKEN")
            if not mcp_token:
                logger.warning("MCP_TOKEN not found - MCP tools may not work properly")
            else:
                logger.info("MCP_TOKEN found - MCP tools should be available")
                
        except Exception as agent_e:
            logger.error(f"Warning: Agent import issue: {agent_e}")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise RuntimeError(f"Failed to initialize services: {e}")
    
    yield
    
    logger.info("Application shutdown complete")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        logger.error(f"Failed to get static agent reference: {e}")
        return {"answerText": "Error: Could not get static agent reference."}

    if session_service is None:
        logger.error("Session service is not initialized")
        return {"answerText": "Error: Session service not initialized."}

    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    initial_content = types.Content(role="user", parts=[types.Part(text=question)])
    final_response = None

    try:
        logger.info(f"Starting agent execution for user {user_id}, session {session_id}")
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
                    logger.warning("Final response event has no content or parts")
                    continue

                response_text = event.content.parts[0].text
                try:
                    final_response = json.loads(response_text)
                except json.JSONDecodeError:
                    final_response = {"answerText": response_text}

        logger.info(f"Agent execution completed for session {session_id}")

    except Exception as e:
        logger.error(f"An error occurred during agent execution for session {session_id}: {e}")
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
            logger.error("Session service is not initialized")
            raise RuntimeError("Session service not initialized")

        logger.info(f"Attempting to get session for user_id={user_id}, session_id={session_id}")

        current_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        if not current_session:
            logger.info(f"Session not found for user {user_id}, session {session_id}. Creating new session.")
            current_session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )

        if not current_session:
            raise RuntimeError(f"Failed to create session for user {user_id}, session {session_id}")

        logger.info(f"Session successfully retrieved/created for user {user_id}, session {session_id}")
        return current_session

    except Exception as e:
        logger.error(f"Error during session lookup/creation for session {session_id}: {e}")
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
            elif existing_request['status'] == 'failed':
                # If it failed due to MCP issues, allow retry after some time
                logger.info(f"Previous request failed, allowing retry for user {request_data.userId}, session {request_data.sessionId}")
                # Reset status to pending for retry
                db_manager.update_status(request_data.userId, request_data.sessionId, "pending")
        
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
        try:
            agent_response = await run_agent_logic(
                    request_data.userId,
                    request_data.sessionId,
                    request_data.question
                )
            logger.info(f"Agent response: {agent_response}")
        except Exception as agent_error:
            logger.error(f"Agent execution failed: {agent_error}")
            db_manager.update_status(request_data.userId, request_data.sessionId, "failed", str(agent_error))
            raise HTTPException(status_code=500, detail="Agent execution failed")

        # NOW get updated session after agent execution
        updated_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=request_data.userId,
            session_id=request_data.sessionId,
        )
        
        logger.info(f"Retrieved session after agent execution: {type(updated_session)}")

        # Check if session exists and has state
        if not updated_session:
            logger.error(f"Session not found after agent execution for user {request_data.userId}, session {request_data.sessionId}")
            raise ValueError("Session not found after agent execution")
        
        if not updated_session.state:
            logger.error(f"Session state is empty after agent execution. Session: {updated_session}")
            logger.error(f"Session type: {type(updated_session)}")
            logger.error(f"Session state: {updated_session.state}")
            raise ValueError("Session state is empty after agent execution")

        logger.info(f"Session state keys: {list(updated_session.state.keys()) if updated_session.state else 'No state'}")
        
        analysis_results_twitter = updated_session.state.get("final_twitter_results", {})
        analysis_results_linkedin = updated_session.state.get("final_linkedin_results", {})
        analysis_results_reddit = updated_session.state.get("final_reddit_results", {})
        analysis_results_news = updated_session.state.get("final_news_results", {})
        
        logger.info(f"Extracted results - Twitter: {bool(analysis_results_twitter)}, LinkedIn: {bool(analysis_results_linkedin)}, Reddit: {bool(analysis_results_reddit)}, News: {bool(analysis_results_news)}")

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
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)