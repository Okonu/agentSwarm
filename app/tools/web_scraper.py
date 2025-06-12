import aiofiles
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)


class WebScraper:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a single URL and return structured content"""
        try:
            response = await self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            for script in soup(["script", "style"]):
                script.decompose()

            content = {
                "url": url,
                "title": soup.title.string if soup.title else "",
                "text": soup.get_text(strip=True, separator=' '),
                "headings": [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])],
                "meta_description": "",
                "links": []
            }

            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                content["meta_description"] = meta_desc.get("content", "")

            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/') or 'infinitepay.io' in href:
                    content["links"].append({
                        "text": link.get_text(strip=True),
                        "href": href
                    })

            return content

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {"url": url, "error": str(e)}

    async def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape multiple URLs concurrently"""
        async with self:
            tasks = [self.scrape_url(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid_results = []
            for result in results:
                if isinstance(result, dict) and "error" not in result:
                    valid_results.append(result)

            return valid_results