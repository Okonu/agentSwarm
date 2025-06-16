import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import httpx
from app.tools.web_scraper import WebScraper
from app.tools.vector_store import VectorStore
from app.tools.customer_tools import CustomerDataTool, TransactionTool


class TestWebScraper:
    @pytest.mark.asyncio
    async def test_scrape_url_success(self):
        scraper = WebScraper()

        result = await scraper.scrape_url("not-a-valid-url")

        assert "url" in result
        assert result["url"] == "not-a-valid-url"
        assert "error" in result

        assert isinstance(result["error"], str)


class TestCustomerDataTool:
    @pytest.mark.asyncio
    async def test_get_customer_info_found(self):
        tool = CustomerDataTool()
        result = await tool.get_customer_info("client789")

        assert result["success"] is True
        assert result["data"]["name"] == "João Silva"
        assert result["data"]["account_status"] == "active"

    @pytest.mark.asyncio
    async def test_get_customer_info_not_found(self):
        tool = CustomerDataTool()
        result = await tool.get_customer_info("nonexistent")

        assert result["success"] is False
        assert result["error"] == "Customer not found"

    @pytest.mark.asyncio
    async def test_check_account_status(self):
        tool = CustomerDataTool()
        result = await tool.check_account_status("client789")

        assert result["success"] is True
        assert result["account_status"] == "active"
        assert isinstance(result["issues"], list)