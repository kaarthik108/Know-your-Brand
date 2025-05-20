import os
import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
# from dotenv import load_dotenv

# Load environment variables
# load_dotenv()

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session DB URL (e.g., SQLite)
# Ensure sessions.db is in a writable location or adjust path
SESSION_DB_URL = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ["*"] # Keeping this as per your setup
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True # Assuming you might want a web interface

# Call the function to get the FastAPI app instance
# The ADK will look for agent packages (like web_search_agent) within AGENT_DIR
app: FastAPI = get_fast_api_app(
    agent_dir=AGENT_DIR, # Directory containing agent packages
    session_db_url=SESSION_DB_URL,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
    # If your agent package is not directly named 'agent' or 'root_agent'
    # or if you have multiple agents, you might need to specify agent_name:
    # agent_name="web_search_agent" # ADK should auto-detect web_search_agent based on folder name
)

if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)