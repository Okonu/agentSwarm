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
        """Test successful URL scraping"""
        mock_html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome</h1>
                <p>This is test content</p>
            </body>
        </html>
        """

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.content = mock_html.encode()
            mock_response.raise_for_status = Mock()

            mock_session = AsyncMock()
            mock_session.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_session

            scraper = WebScraper()
            async with scraper:
                result = await scraper.scrape_url("https://example.com")

            assert result["url"] == "https://example.com"
            assert result["title"] == "Test Page"
            assert "Welcome" in result["text"]
            assert "This is test content" in result["text"]


class TestCustomerDataTool:
    @pytest.mark.asyncio
    async def test_get_customer_info_found(self):
        """Test getting existing customer information"""
        tool = CustomerDataTool()
        result = await tool.get_customer_info("client789")

        assert result["success"] is True
        assert result["data"]["name"] == "João Silva"
        assert result["data"]["account_status"] == "active"

    @pytest.mark.asyncio
    async def test_get_customer_info_not_found(self):
        """Test getting non-existent customer information"""
        tool = CustomerDataTool()
        result = await tool.get_customer_info("nonexistent")

        assert result["success"] is False
        assert result["error"] == "Customer not found"

    @pytest.mark.asyncio
    async def test_check_account_status(self):
        """Test checking account status"""
        tool = CustomerDataTool()
        result = await tool.check_account_status("client789")

        assert result["success"] is True
        assert result["account_status"] == "active"
        assert isinstance(result["issues"], list)