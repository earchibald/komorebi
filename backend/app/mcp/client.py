"""MCP client for connecting to external MCP servers.

Implements the client side of the Model Context Protocol
for communicating with MCP servers like GitHub, Jira, etc.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from ..models.mcp import MCPServerConfig, MCPServerStatus, MCPTool


@dataclass
class MCPMessage:
    """Message in the MCP JSON-RPC protocol."""
    
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: Optional[str] = None
    params: Optional[dict] = None
    result: Optional[Any] = None
    error: Optional[dict] = None


class MCPClient:
    """Client for connecting to an MCP server.
    
    Uses subprocess to spawn the MCP server and communicates
    via stdin/stdout using the JSON-RPC protocol.
    """
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._tools: list[MCPTool] = []
        self._reader_task: Optional[asyncio.Task] = None
    
    @property
    def status(self) -> MCPServerStatus:
        """Get current connection status."""
        return self.config.status
    
    @property
    def tools(self) -> list[MCPTool]:
        """Get available tools from this server."""
        return self._tools
    
    async def connect(self) -> bool:
        """Start the MCP server and establish connection.
        
        Returns True if connection was successful.
        """
        if self._process is not None:
            return True
        
        try:
            self.config.status = MCPServerStatus.CONNECTING
            
            # Prepare environment
            env = dict(self.config.env) if self.config.env else {}
            
            # Start the server process
            self._process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env if env else None,
            )
            
            # Start reader task
            self._reader_task = asyncio.create_task(self._read_responses())
            
            # Initialize the connection
            await self._initialize()
            
            self.config.status = MCPServerStatus.CONNECTED
            self.config.last_error = None
            return True
            
        except Exception as e:
            self.config.status = MCPServerStatus.ERROR
            self.config.last_error = str(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None
        
        self.config.status = MCPServerStatus.DISCONNECTED
        self._tools = []
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        response = await self._request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return response.get("content", [])
    
    async def _initialize(self) -> None:
        """Initialize the MCP connection."""
        # Send initialize request
        await self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "komorebi",
                "version": "0.1.0",
            },
        })
        
        # Send initialized notification
        await self._notify("notifications/initialized", {})
        
        # List available tools
        tools_response = await self._request("tools/list", {})
        self._tools = [
            MCPTool(
                name=t["name"],
                description=t.get("description"),
                server_id=self.config.id,
                input_schema=t.get("inputSchema", {}),
            )
            for t in tools_response.get("tools", [])
        ]
    
    async def _request(self, method: str, params: dict) -> dict:
        """Send a request and wait for response."""
        if not self._process or not self._process.stdin:
            raise RuntimeError("Not connected to MCP server")
        
        self._request_id += 1
        request_id = self._request_id
        
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        try:
            # Send request
            data = json.dumps(message) + "\n"
            self._process.stdin.write(data.encode())
            await self._process.stdin.drain()
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
            
        finally:
            self._pending_requests.pop(request_id, None)
    
    async def _notify(self, method: str, params: dict) -> None:
        """Send a notification (no response expected)."""
        if not self._process or not self._process.stdin:
            raise RuntimeError("Not connected to MCP server")
        
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        
        data = json.dumps(message) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()
    
    async def _read_responses(self) -> None:
        """Background task to read responses from the server."""
        if not self._process or not self._process.stdout:
            return
        
        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break
                
                try:
                    message = json.loads(line.decode())
                    
                    if "id" in message and message["id"] in self._pending_requests:
                        future = self._pending_requests.get(message["id"])
                        if future and not future.done():
                            if "error" in message:
                                future.set_exception(
                                    RuntimeError(message["error"].get("message", "Unknown error"))
                                )
                            else:
                                future.set_result(message.get("result", {}))
                                
                except json.JSONDecodeError:
                    continue
                    
        except asyncio.CancelledError:
            pass
