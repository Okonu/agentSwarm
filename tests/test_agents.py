import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.agents.router_agent import RouterAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.support_agent import SupportAgent
from app.agents.personality_agent import PersonalityAgent
from app.core.llm_client import LLMClient
from app.tools.vector_store import VectorStore
from app.models.schemas import AgentType


@pytest.fixture
def mock_llm_client():
    client = Mock(spec=LLMClient)
    client.generate_response_with_system_prompt = AsyncMock()
    return client


@pytest.fixture
def mock_vector_store():
    store = Mock(spec=VectorStore)
    store.search = AsyncMock()
    return store


class TestRouterAgent:
    @pytest.mark.asyncio
    async def test_router_agent_routes_to_knowledge(self, mock_llm_client):
        mock_llm_client.generate_response_with_system_prompt.return_value = '''
        {
            "agent": "KNOWLEDGE",
            "reasoning": "Question about product pricing",
            "priority": "medium",
            "context": {"user_intent": "product_pricing", "query_type": "pricing"}
        }
        '''

        router = RouterAgent(mock_llm_client)
        response = await router.process("What are the fees for Maquininha Smart?")

        assert response.agent_name == "Router"
        assert response.agent_type == AgentType.ROUTER
        assert response.metadata["agent"] == "KNOWLEDGE"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "route_analysis"

    @pytest.mark.asyncio
    async def test_router_agent_routes_to_support(self, mock_llm_client):
        mock_llm_client.generate_response_with_system_prompt.return_value = '''
        {
            "agent": "SUPPORT",
            "reasoning": "Account access issue",
            "priority": "high",
            "context": {"user_intent": "account_help", "query_type": "account_issue"}
        }
        '''

        router = RouterAgent(mock_llm_client)
        response = await router.process("I can't sign in to my account")

        assert response.metadata["agent"] == "SUPPORT"
        assert response.metadata["priority"] == "high"

    @pytest.mark.asyncio
    async def test_router_agent_handles_invalid_json(self, mock_llm_client):
        mock_llm_client.generate_response_with_system_prompt.return_value = "Invalid JSON response"

        router = RouterAgent(mock_llm_client)
        response = await router.process("Some query")

        assert response.metadata["agent"] == "KNOWLEDGE"
        assert response.metadata["reasoning"] == "Default routing due to parsing error"


class TestKnowledgeAgent:
    @pytest.mark.asyncio
    async def test_knowledge_agent_uses_rag_for_infinitepay_query(self, mock_llm_client, mock_vector_store):
        mock_vector_store.search_enhanced.return_value = [
            {
                "document": "Maquininha Smart fees are 2.5% for credit cards",
                "metadata": {"url": "https://infinitepay.io/maquininha", "title": "Maquininha Smart"},
                "similarity": 0.9
            }
        ]

        mock_vector_store.extract_pricing_insights.return_value = {
            "has_pricing_data": True,
            "payment_methods": ["credit"],
            "rate_ranges": {},
            "volume_tiers": [],
            "specific_rates": []
        }

        mock_llm_client.generate_response_with_system_prompt.return_value = "The Maquininha Smart has fees of 2.5% for credit cards."

        knowledge_agent = KnowledgeAgent(mock_llm_client, mock_vector_store)
        response = await knowledge_agent.process("What are the fees for Maquininha Smart?")

        assert response.agent_name == "Knowledge"
        assert response.agent_type == AgentType.KNOWLEDGE
        assert any(tc.tool_name == "enhanced_rag_retrieval" for tc in response.tool_calls)
        mock_vector_store.search_enhanced.assert_called_once()

    @pytest.mark.asyncio
    async def test_knowledge_agent_uses_web_search_for_general_query(self, mock_llm_client, mock_vector_store):
        mock_llm_client.generate_response_with_system_prompt.return_value = "Palmeiras last game was yesterday."

        knowledge_agent = KnowledgeAgent(mock_llm_client, mock_vector_store)

        with patch.object(knowledge_agent, 'web_search') as mock_web_search:
            mock_web_search.search = AsyncMock(return_value=[
                {"title": "Palmeiras Results", "snippet": "Palmeiras won 2-1", "source": "Sports News"}
            ])

            response = await knowledge_agent.process("Quando foi o último jogo do Palmeiras?")

            assert any(tc.tool_name == "web_search" for tc in response.tool_calls)
            mock_web_search.search.assert_called_once()


class TestSupportAgent:
    @pytest.mark.asyncio
    async def test_support_agent_gets_customer_info(self, mock_llm_client):
        mock_llm_client.generate_response_with_system_prompt.return_value = "I can help you with your account issue."

        support_agent = SupportAgent(mock_llm_client)

        with patch.object(support_agent.customer_tool, 'get_customer_info') as mock_get_info:
            mock_get_info.return_value = {
                "success": True,
                "data": {"name": "João Silva", "account_status": "active"}
            }

            with patch.object(support_agent.customer_tool, 'check_account_status') as mock_check_status:
                mock_check_status.return_value = {
                    "success": True,
                    "account_status": "active",
                    "issues": []
                }

                response = await support_agent.process(
                    "I can't make transfers",
                    context={"user_id": "client789"}
                )

                assert response.agent_name == "Support"
                assert any(tc.tool_name == "get_customer_info" for tc in response.tool_calls)
                assert any(tc.tool_name == "check_account_status" for tc in response.tool_calls)
                assert response.metadata["customer_found"] is True


class TestPersonalityAgent:
    @pytest.mark.asyncio
    async def test_personality_agent_enhances_response(self, mock_llm_client):
        mock_llm_client.generate_response_with_system_prompt.return_value = "I'd be happy to help! The Maquininha Smart fees are 2.5% for credit cards. Let me know if you have any other questions!"

        personality_agent = PersonalityAgent(mock_llm_client)

        context = {
            "source_response": "Maquininha Smart fees: 2.5% credit cards",
            "original_query": "What are the fees?",
            "source_agent": "Knowledge"
        }

        response = await personality_agent.process("What are the fees?", context)

        assert response.agent_name == "Personality"
        assert response.agent_type == AgentType.PERSONALITY
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "personality_enhancement"
        assert len(response.response) > len(context["source_response"])