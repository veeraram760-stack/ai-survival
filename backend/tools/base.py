"""
Base tool classes for agent capabilities
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger("ai_survival.tools")


class Tool(ABC):
    """Base class for all agent tools"""

    def __init__(self, name: str, description: str, cost: float = 0.0):
        self.name = name
        self.description = description
        self.cost = cost  # Cost in dollars per use
        self.usage_count = 0

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "cost": self.cost,
            "usage_count": self.usage_count,
        }


class ToolRegistry:
    """Registry for managing available tools"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        return {name: tool.get_metadata() for name, tool in self._tools.items()}

    async def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"status": "failed", "error": f"Tool '{name}' not found"}
        tool.usage_count += 1
        return await tool.execute(**kwargs)


# Global tool registry
tool_registry = ToolRegistry()