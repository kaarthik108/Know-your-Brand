from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Higher-order function to execute a tool with proper cleanup
async def execute_tool(tool, args):
    """Execute a single tool and handle cleanup."""
    try:
        result = await tool.run_async(args=args, tool_context=None)
        return (True, result, None)  # Success, result, no error
    except Exception as e:
        return (False, None, str(e))  # Failed, no result, error message


# Function to try tools sequentially until one succeeds
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


# Create a higher-order function that handles connection and resource management
def create_mcp_tool_executor(command, args=None, env=None):
    """Create a function that connects to an MCP server and executes tools."""
    async def mcp_tool_executor(**kwargs):
        # Connect to MCP server
        tools, exit_stack = await MCPToolset.from_server(
            connection_params=StdioServerParameters(
                command='npx',
                args=["-y", "@brightdata/mcp"],
                env={
                    "API_TOKEN": "9bc84098-141c-4933-bd41-da6842e69427",
                    "WEB_UNLOCKER_ZONE": "web_unlocker1",
                    # "BROWSER_AUTH": "SBR_USER:SBR_PASS"
                }
            )
        )
        try:
            # Try all tools until one succeeds
            return await try_tools_sequentially(tools, kwargs, exit_stack)
        finally:
            # Always cleanup
            await exit_stack.aclose()
    
    return mcp_tool_executor


# Create our web search function
search_web = create_mcp_tool_executor(
    command="mcp-web-search",
    args=[],
)

search_web.__name__ = "search_web"
search_web.__doc__ = "Search the web for information based on the provided query."