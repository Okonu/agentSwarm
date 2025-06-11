from typing import Dict, List, Any
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentCommunicationHub:
    """Manages communication between agents"""

    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.message_history: List[Dict[str, Any]] = []
        self.workflow_log: List[Dict[str, Any]] = []

    def register_agent(self, agent_name: str, agent_instance):
        """Register an agent with the communication hub"""
        self.agents[agent_name] = agent_instance
        logger.info(f"Registered agent: {agent_name}")

    async def send_message(self, from_agent: str, to_agent: str, message: str, context: Dict[str, Any] = None):
        """Send a message from one agent to another"""
        if to_agent not in self.agents:
            raise ValueError(f"Agent {to_agent} not found")

        comm_log = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        self.message_history.append(comm_log)

        response = await self.agents[to_agent].process(message, context)

        workflow_step = {
            "agent_name": to_agent,
            "tool_calls": {tc.tool_name: tc.tool_output for tc in response.tool_calls}
        }
        self.workflow_log.append(workflow_step)

        return response

    def get_workflow_log(self) -> List[Dict[str, Any]]:
        """Get the current workflow log"""
        return self.workflow_log.copy()

    def reset_workflow(self):
        """Reset the workflow log for a new request"""
        self.workflow_log.clear()