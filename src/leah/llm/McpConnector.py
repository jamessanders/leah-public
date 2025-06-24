import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
import threading

class McpToolsSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(McpToolsSingleton, cls).__new__(cls)
                cls._instance._init_tools()
        return cls._instance

    def _init_tools(self):
        self.mcp_client = MultiServerMCPClient(
            {
                "serena": {
                    "command": "/opt/homebrew/bin/uv",
                    "args": ["run", "--directory", "/Users/jsanders/Code/serena", "serena-mcp-server"],
                    "transport": "stdio"
                }
            }
        )
        self.mcp_tools = asyncio.run(self.mcp_client.get_tools())

    @classmethod
    def get_instance(cls):
        return cls()

    def get_tools(self):
        return self.mcp_tools
