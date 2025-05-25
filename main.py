import os
import uvicorn
# from google.adk.cli.fast_api import get_fast_api_app
# from dotenv import load_dotenv
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.runners import Runner
# from google.adk.sessions import DatabaseSessionService
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mcp_brand_agent.agent import root_agent

# Load environment variables
load_dotenv('.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_NAME = os.environ.get("APP_NAME", "mcp_brand_agent")
# SESSION_DB_URL = os.environ.get("SESSION_DB_URL")

# if not SESSION_DB_URL:
#     raise ValueError("SESSION_DB_URL environment variable is required")

ALLOWED_ORIGINS = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/query")
async def query_endpoint(request_data: QueryRequest):
    try:

        # Get or create session
        await get_or_create_session(
            request_data.userId,
            request_data.sessionId
        )
        # Run agent logic
        await run_agent_logic(
            request_data.userId, request_data.sessionId, request_data.question
        )

        # Get updated session after agent execution
        updated_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=request_data.userId,
            session_id=request_data.sessionId,
        )
        analysis_results_twitter = updated_session.state.get("final_twitter_results", {})
        analysis_results_linkedin = updated_session.state.get("final_linkedin_results", {})
        analysis_results_reddit = updated_session.state.get("final_reddit_results", {})
        analysis_results_news = updated_session.state.get("final_news_results", {})
        
        print(f"Analysis results:\n\n {analysis_results_twitter}\n\n")
        if isinstance(analysis_results_twitter, str) or isinstance(analysis_results_linkedin, str) or isinstance(analysis_results_reddit, str) or isinstance(analysis_results_news, str):
            try:
                import json

                analysis_results_twitter = json.loads(analysis_results_twitter)
                analysis_results_linkedin = json.loads(analysis_results_linkedin)
                analysis_results_reddit = json.loads(analysis_results_reddit)
                analysis_results_news = json.loads(analysis_results_news)
            except json.JSONDecodeError:
                analysis_results_twitter = {"analysis_results_twitter": analysis_results_twitter}
                analysis_results_linkedin = {"analysis_results_linkedin": analysis_results_linkedin}
                analysis_results_reddit = {"analysis_results_reddit": analysis_results_reddit}
                analysis_results_news = {"analysis_results_news": analysis_results_news}

        response_data = {
            "userId": request_data.userId,
            "sessionId": request_data.sessionId,
            "analysis_results_twitter": analysis_results_twitter if analysis_results_twitter else {},
            "analysis_results_linkedin": analysis_results_linkedin if analysis_results_linkedin else {},
            "analysis_results_reddit": analysis_results_reddit if analysis_results_reddit else {},
            "analysis_results_news": analysis_results_news if analysis_results_news else {}
        }
        return response_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unhandled exception in query_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")


if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)