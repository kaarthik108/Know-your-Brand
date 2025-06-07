import os
import dotenv
import asyncio
from typing import Any, Dict

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from langchain_mcp_adapters.client import MultiServerMCPClient

# from google.adk.tools.langchain_tool import LangchainTool
# from langchain_mcp_adapters.client import MultiServerMCPClient

dotenv.load_dotenv('.env')

async def execute_tool(tool, args):
    """Execute a single tool and handle cleanup."""
    try:
        result = await tool.run_async(args=args, tool_context=None)
        return (True, result, None)
    except Exception as e:
        return (False, None, str(e)) 


async def try_tools_sequentially(tools, args, exit_stack):
    """Try each tool in sequence until one succeeds."""
    errors = []
    
    for tool in tools:
        success, result, error = await execute_tool(tool, args)
        if success:
            return result
        errors.append(f"Tool '{tool.name}' failed: {error}")
    
    if errors:
        return f"All tools failed: {'; '.join(errors)}"
    return "No tools available"


def create_mcp_tool_executor(command, args=None, env=None):
    """Create a function that connects to an MCP server and executes tools."""
    async def mcp_tool_executor(**kwargs):
        tools, exit_stack = await MCPToolset(
            connection_params=StdioServerParameters(
                command='npx',
                args=["-y", "@brightdata/mcp"],
                env={
                    "API_TOKEN": os.getenv("MCP_TOKEN"),
                    # "WEB_UNLOCKER_ZONE": "web_unlocker1",
                    # "BROWSER_AUTH": "SBR_USER:SBR_PASS"
                }
            )
        )
        try:
            return await try_tools_sequentially(tools, kwargs, exit_stack)
        finally:
            await exit_stack.aclose()
    
    return mcp_tool_executor


# Create our web search function
search_web = create_mcp_tool_executor(
    command="mcp-web-search",
    args=[]
)

search_web.__name__ = "search_web"
search_web.__doc__ = "Search the web for information based on the provided query."

# client = MultiServerMCPClient(
#     {
#         "mcp": {
#             "command": "npx",
#             "args": ["-y", "@brightdata/mcp"],
#             "transport": "stdio",
#             "env": {
#                 "API_TOKEN": os.getenv("MCP_TOKEN"),
#                 "WEB_UNLOCKER_ZONE": "web_unlocker1",
#             }
#         }
#     }
# )

# def search_web_sync(query: str) -> Dict[str, Any]:
#     """Synchronous wrapper for web search functionality"""
#     async def _search():
#         try:
#             api_token = os.getenv("MCP_TOKEN")
#             if not api_token:
#                 raise ValueError("MCP_TOKEN environment variable is required")
            
#             tools = await client.get_tools()
            
#             for tool in tools:
#                 if hasattr(tool, 'name') and 'search' in tool.name.lower():
#                     result = await tool.ainvoke({"query": query})
#                     return result
            
#             return {"error": "No search tool found"}
            
#         except Exception as e:
#             return {"error": f"Search failed: {str(e)}"}
    
#     try:
#         loop = asyncio.get_event_loop()
#         if loop.is_running():
#             import concurrent.futures
#             with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
#                 future = executor.submit(asyncio.run, _search())
#                 return future.result()
#         else:
#             return asyncio.run(_search())
#     except Exception as e:
#         return {"error": f"Failed to execute search: {str(e)}"}

# search_web = search_web_sync
# search_web.__name__ = "search_web"
# search_web.__doc__ = "Search the web for information based on the provided query."