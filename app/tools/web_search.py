import httpx
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class WebSearchTool:

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        try:

            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "pretty": "1",
                "no_redirect": "1"
            }

            async with self:
                response = await self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []

                if data.get("Abstract"):
                    results.append({
                        "title": data.get("Heading", ""),
                        "snippet": data.get("Abstract", ""),
                        "url": data.get("AbstractURL", ""),
                        "source": "DuckDuckGo Abstract"
                    })

                for topic in data.get("RelatedTopics", [])[:max_results - len(results)]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "")[:100] + "...",
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                            "source": "DuckDuckGo Related"
                        })

                return results[:max_results]

        except Exception as e:
            logger.error(f"Error in web search: {str(e)}")
            return [{"error": f"Search failed: {str(e)}"}]