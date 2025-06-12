import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_endpoint_product_query():
    with patch('app.main.orchestrator') as mock_orchestrator:
        mock_orchestrator.is_initialized = True
        mock_orchestrator.process_message = AsyncMock(return_value={
            "response": "I'd be happy to help! The Maquininha Smart has competitive rates for credit card transactions.",
            "source_agent_response": "Maquininha Smart rates: 2.5% credit cards",
            "agent_workflow": [
                {"agent_name": "router", "tool_calls": {"route_analysis": {"agent": "KNOWLEDGE"}}},
                {"agent_name": "knowledge", "tool_calls": {"rag_retrieval": {"results_count": 3}}},
                {"agent_name": "personality", "tool_calls": {"personality_enhancement": True}}
            ]
        })

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat",
                json={"message": "What are the fees for Maquininha Smart?", "user_id": "client789"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "source_agent_response" in data
        assert "agent_workflow" in data
        assert len(data["agent_workflow"]) == 3


@pytest.mark.asyncio
async def test_chat_endpoint_support_query():
    with patch('app.main.orchestrator') as mock_orchestrator:
        mock_orchestrator.is_initialized = True
        mock_orchestrator.process_message = AsyncMock(return_value={
            "response": "I understand your concern about account access. Let me check your account status.",
            "source_agent_response": "Account status: active, no issues found",
            "agent_workflow": [
                {"agent_name": "router", "tool_calls": {"route_analysis": {"agent": "SUPPORT"}}},
                {"agent_name": "support",
                 "tool_calls": {"get_customer_info": {"success": True}, "check_account_status": {"success": True}}},
                {"agent_name": "personality", "tool_calls": {"personality_enhancement": True}}
            ]
        })

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat",
                json={"message": "I can't sign in to my account", "user_id": "client789"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "I understand your concern" in data["response"]