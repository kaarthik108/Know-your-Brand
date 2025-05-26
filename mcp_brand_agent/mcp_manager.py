# import os
# import asyncio
# from typing import Optional
# from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# class MCPManager:
#     """Singleton manager for MCP toolset to avoid multiple process creation"""
    
#     _instance: Optional['MCPManager'] = None
#     _toolset: Optional[MCPToolset] = None
#     _lock = asyncio.Lock()
    
#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#         return cls._instance
    
#     async def get_toolset(self) -> MCPToolset:
#         """Get or create the MCP toolset instance"""
#         if self._toolset is None:
#             async with self._lock:
#                 if self._toolset is None:  # Double-check locking
#                     self._toolset = MCPToolset(
#                         connection_params=StdioServerParameters(
#                             command='npx',
#                             args=["-y", "@brightdata/mcp"],
#                             env={
#                                 "API_TOKEN": os.getenv("MCP_TOKEN"),
#                                 "WEB_UNLOCKER_ZONE": "web_unlocker1",
#                             }
#                         )
#                     )
#         return self._toolset
    
#     def get_toolset_sync(self) -> MCPToolset:
#         """Synchronous version for non-async contexts"""
#         if self._toolset is None:
#             self._toolset = MCPToolset(
#                 connection_params=StdioServerParameters(
#                     command='npx',
#                     args=["-y", "@brightdata/mcp"],
#                     env={
#                         "API_TOKEN": os.getenv("MCP_TOKEN"),
#                         "WEB_UNLOCKER_ZONE": "web_unlocker1",
#                     }
#                 )
#             )
#         return self._toolset

# # Global instance
# mcp_manager = MCPManager() 