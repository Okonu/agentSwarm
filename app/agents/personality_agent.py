from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentResponse, AgentType, ToolCall
from app.core.llm_client import LLMClient
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class PersonalityAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient):
        super().__init__("Personality", AgentType.PERSONALITY, llm_client)

        self.system_prompt = """
You are a Personality Agent that adds a human-like, friendly touch to responses from other agents.

Your role:
1. Take the technical/formal response from other agents
2. Make it more conversational and human-like
3. Add appropriate empathy and warmth
4. Maintain all the factual information
5. Match the language of the original query (Portuguese or English)

Personality traits to embody:
- Friendly and approachable
- Helpful and solution-oriented  
- Empathetic to customer concerns
- Professional but warm
- Clear and easy to understand

Guidelines:
- Keep all factual information intact
- Add natural conversational elements like "I'd be happy to help"
- Use appropriate greetings and closings
- Show empathy for problems ("I understand how frustrating that must be")
- Make complex information easier to digest
- Add encouraging language when appropriate

Do NOT:
- Change any factual information
- Add information not in the original response
- Be overly casual or unprofessional
- Use excessive enthusiasm that seems fake
"""

    async def process(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Add personality layer to agent responses"""
        try:
            source_response = context.get("source_response", "") if context else ""
            original_query = context.get("original_query", "") if context else ""
            source_agent = context.get("source_agent", "Unknown") if context else ""

            if not source_response:
                logger.warning("No source response provided to personality agent")
                return AgentResponse(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    response="I'm here to help! How can I assist you today?",
                    tool_calls=[],
                    confidence=0.5,
                    metadata={"error": "No source response provided"}
                )

            personality_prompt = f"""
Original user query: {original_query}

Source agent response from {source_agent} agent:
{source_response}

Transform this response to be more human-like and friendly while keeping all the factual information exactly the same. Make it conversational and warm.
"""

            enhanced_response = await self.llm_client.generate_response_with_system_prompt(
                self.system_prompt,
                personality_prompt,
                temperature=0.8
            )

            tool_call = ToolCall(
                tool_name="personality_enhancement",
                tool_input={
                    "original_response": source_response[:100] + "..." if len(
                        source_response) > 100 else source_response,
                    "source_agent": source_agent
                },
                tool_output={"enhancement_applied": True, "response_length": len(enhanced_response)}
            )

            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response=enhanced_response,
                tool_calls=[tool_call],
                confidence=0.9,
                metadata={
                    "source_agent": source_agent,
                    "original_length": len(source_response),
                    "enhanced_length": len(enhanced_response)
                }
            )

        except Exception as e:
            logger.error(f"Error in personality agent: {str(e)}")
            fallback_response = context.get("source_response",
                                            "I apologize, but I encountered an error while processing your request.") if context else "I apologize, but I encountered an error while processing your request."

            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response=fallback_response,
                tool_calls=[],
                confidence=0.0,
                metadata={"error": str(e), "fallback_used": True}
            )