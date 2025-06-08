import os
import dotenv

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# from langchain_mcp_adapters.client import MultiServerMCPClient

# from google.adk.tools.langchain_tool import LangchainTool
# from langchain_mcp_adapters.client import MultiServerMCPClient

dotenv.load_dotenv('.env')

search_web = MCPToolset(
    connection_params=StdioServerParameters(
        command="npx", 
        args=["-y", "@brightdata/mcp"],
        env={
            "API_TOKEN": os.getenv("MCP_TOKEN"),
            "WEB_UNLOCKER_ZONE": "web_unlocker1",
        }
    ),
)