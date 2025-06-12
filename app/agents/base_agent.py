from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.models.schemas import AgentResponse, AgentType, ToolCall
from app.core.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(self, name: str, agent_type: AgentType, llm_client: LLMClient):
        self.name = name
        self.agent_type = agent_type
        self.llm_client = llm_client
        self.tools = {}
        self.system_prompt = ""

    @abstractmethod
    async def process(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        pass

    def add_tool(self, name: str, tool_func):
        self.tools[name] = tool_func

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        try:
            result = await self.tools[tool_name](**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            raise

    def get_system_prompt(self) -> str:
        return self.system_prompt