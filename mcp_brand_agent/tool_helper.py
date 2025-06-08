import os
import dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient

dotenv.load_dotenv('.env')

client = MultiServerMCPClient(
    {
        "mcp": {
            "command": "npx",
            "args": ["-y", "@brightdata/mcp"],
            "transport": "stdio",
            "env": {
                "API_TOKEN": os.getenv("MCP_TOKEN"),
                "WEB_UNLOCKER_ZONE": "web_unlocker1",
            }
        }
    }
)

def search_web_sync(query: str):
    """Synchronous wrapper for web search functionality"""
    async def _search():
        try:
            api_token = os.getenv("MCP_TOKEN")
            if not api_token:
                raise ValueError("MCP_TOKEN environment variable is required")
            
            tools = await client.get_tools()
            
            for tool in tools:
                if hasattr(tool, 'name') and 'search' in tool.name.lower():
                    result = await tool.ainvoke({"query": query})
                    return result
            
            return {"error": "No search tool found"}
            
        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}

search_web = search_web_sync
search_web.__name__ = "search_web"
search_web.__doc__ = "Search the web for information based on the provided query."