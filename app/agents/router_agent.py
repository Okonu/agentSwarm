from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentResponse, AgentType, ToolCall
from app.core.llm_client import LLMClient
from typing import Dict, Any
import logging
import json

logger = logging.getLogger(__name__)


class RouterAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient):
        super().__init__("Router", AgentType.ROUTER, llm_client)
        self.system_prompt = """
You are a Router Agent responsible for analyzing user messages and determining which specialized agent should handle the request.

Available agents:
1. KNOWLEDGE - Handles questions about InfinitePay products, services, fees, and general information
2. SUPPORT - Handles customer support issues, account problems, technical issues, and user-specific queries

Analyze the user message and respond with a JSON object containing:
{
    "agent": "KNOWLEDGE" or "SUPPORT",
    "reasoning": "Brief explanation of why this agent was chosen",
    "priority": "high", "medium", or "low",
    "context": {
        "user_intent": "description of what user wants",
        "query_type": "product_info", "pricing", "technical_support", "account_issue", etc.
    }
}

Examples:
- "What are the fees for Maquininha Smart?" -> KNOWLEDGE (product pricing info)
- "How can I use my phone as a card machine?" -> KNOWLEDGE (product features)
- "I can't sign in to my account" -> SUPPORT (account access issue)
- "Why can't I make transfers?" -> SUPPORT (account functionality issue)
- "What is PIX?" -> KNOWLEDGE (product/service information)

Always respond with valid JSON only.
"""

    async def process(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Analyze message and route to appropriate agent"""
        try:
            response_text = await self.llm_client.generate_response_with_system_prompt(
                self.system_prompt,
                f"User message: {message}",
                temperature=0.1
            )

            try:
                routing_decision = json.loads(response_text.strip())
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse routing JSON: {response_text}")
                routing_decision = {
                    "agent": "KNOWLEDGE",
                    "reasoning": "Default routing due to parsing error",
                    "priority": "medium",
                    "context": {"user_intent": "unknown", "query_type": "general"}
                }

            tool_call = ToolCall(
                tool_name="route_analysis",
                tool_input={"message": message},
                tool_output=routing_decision
            )

            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response=f"Routing to {routing_decision['agent']} agent: {routing_decision['reasoning']}",
                tool_calls=[tool_call],
                confidence=0.9,
                metadata=routing_decision
            )

        except Exception as e:
            logger.error(f"Error in router agent: {str(e)}")
            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response="Routing to KNOWLEDGE agent (fallback)",
                tool_calls=[],
                confidence=0.5,
                metadata={"agent": "KNOWLEDGE", "reasoning": "Error fallback"}
            )