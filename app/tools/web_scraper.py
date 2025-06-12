import aiofiles
import httpx
from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Optional
import logging
import asyncio
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PricingInfo:
    product: str
    payment_method: str
    rate: str
    rate_numeric: Optional[float]
    conditions: str
    volume_tier: Optional[str] = None


@dataclass
class DocumentChunk:
    content: str
    chunk_type: str
    metadata: Dict[str, Any]
    pricing_data: List[PricingInfo] = None


class WebScraper:
    def __init__(self):
        self.session = None
        self.pricing_patterns = [
            r'(\d+\.?\d*)\%',
            r'R\$\s*(\d+[,.]?\d*)',
            r'(\d+)x\s*(?:de\s*)?R\$\s*(\d+[,.]?\d*)',
        ]

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    def extract_pricing_tables(self, soup: BeautifulSoup) -> List[PricingInfo]:
        pricing_data = []

        for table in soup.find_all('table'):
            pricing_data.extend(self._parse_html_table(table))

        pricing_sections = soup.find_all(['div', 'section'], class_=re.compile(r'(rate|price|fee|cost)', re.I))
        for section in pricing_sections:
            pricing_data.extend(self._parse_pricing_section(section))

        text_content = soup.get_text()
        pricing_data.extend(self._extract_pricing_from_text(text_content))

        return pricing_data

    def _parse_html_table(self, table: Tag) -> List[PricingInfo]:
        pricing_data = []
        headers = []

        header_row = table.find('tr')
        if header_row:
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

        for row in table.find_all('tr')[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
            if len(cells) >= 2:
                pricing_data.append(self._create_pricing_info_from_row(cells, headers))

        return [p for p in pricing_data if p]

    def _parse_pricing_section(self, section: Tag) -> List[PricingInfo]:
        pricing_data = []
        text = section.get_text()

        lines = text.split('\n')
        current_product = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if any(keyword in line.lower() for keyword in ['machine', 'tap', 'link', 'pix', 'smart']):
                current_product = line

            pricing_info = self._extract_pricing_from_line(line, current_product)
            if pricing_info:
                pricing_data.append(pricing_info)

        return pricing_data

    def _extract_pricing_from_text(self, text: str) -> List[PricingInfo]:
        pricing_data = []
        lines = text.split('\n')

        for line in lines:
            if any(keyword in line.lower() for keyword in ['rate', 'fee', '%', 'r$']):
                pricing_info = self._extract_pricing_from_line(line)
                if pricing_info:
                    pricing_data.append(pricing_info)

        return pricing_data

    def _extract_pricing_from_line(self, line: str, product: str = None) -> Optional[PricingInfo]:
        line_lower = line.lower()

        payment_method = "unknown"
        if "pix" in line_lower:
            payment_method = "pix"
        elif "debit" in line_lower:
            payment_method = "debit"
        elif "credit" in line_lower:
            payment_method = "credit"
        elif "boleto" in line_lower:
            payment_method = "boleto"

        rate_match = re.search(r'(\d+\.?\d*)\%', line)
        rate_str = "0%" if "free" in line_lower or "zero" in line_lower else None
        rate_numeric = None

        if rate_match:
            rate_str = rate_match.group(0)
            rate_numeric = float(rate_match.group(1))
        elif rate_str == "0%":
            rate_numeric = 0.0

        volume_tier = None
        if "above" in line_lower or "up to" in line_lower or "from" in line_lower:
            volume_match = re.search(r'(\d+[,.]?\d*)\s*(?:thousand|mil)', line_lower)
            if volume_match:
                volume_tier = volume_match.group(0)

        if rate_str and payment_method != "unknown":
            return PricingInfo(
                product=product or "general",
                payment_method=payment_method,
                rate=rate_str,
                rate_numeric=rate_numeric,
                conditions=line.strip(),
                volume_tier=volume_tier
            )

        return None

    def _create_pricing_info_from_row(self, cells: List[str], headers: List[str]) -> Optional[PricingInfo]:
        if len(cells) < 2:
            return None

        payment_method = cells[0].lower() if cells else "unknown"
        rate = cells[1] if len(cells) > 1 else ""

        rate_numeric = None
        rate_match = re.search(r'(\d+\.?\d*)', rate)
        if rate_match:
            rate_numeric = float(rate_match.group(1))

        return PricingInfo(
            product="table_data",
            payment_method=payment_method,
            rate=rate,
            rate_numeric=rate_numeric,
            conditions=" | ".join(cells)
        )

    def chunk_document_content(self, soup: BeautifulSoup, url: str) -> List[DocumentChunk]:
        chunks = []

        pricing_data = self.extract_pricing_tables(soup)

        if pricing_data:
            pricing_text = self._format_pricing_data(pricing_data)
            chunks.append(DocumentChunk(
                content=pricing_text,
                chunk_type="pricing_table",
                metadata={"url": url, "data_type": "structured_pricing"},
                pricing_data=pricing_data
            ))

        for header in soup.find_all(['h1', 'h2', 'h3']):
            if header.get_text(strip=True):
                chunks.append(DocumentChunk(
                    content=header.get_text(strip=True),
                    chunk_type="header",
                    metadata={"url": url, "header_level": header.name}
                ))

        for list_elem in soup.find_all(['ul', 'ol']):
            list_text = []
            for li in list_elem.find_all('li'):
                list_text.append(f"• {li.get_text(strip=True)}")

            if list_text:
                chunks.append(DocumentChunk(
                    content="\n".join(list_text),
                    chunk_type="feature_list",
                    metadata={"url": url, "item_count": len(list_text)}
                ))

        paragraphs = soup.find_all('p')
        for i, para in enumerate(paragraphs):
            text = para.get_text(strip=True)
            if len(text) > 50:
                chunks.append(DocumentChunk(
                    content=text,
                    chunk_type="text",
                    metadata={"url": url, "paragraph_index": i}
                ))

        return chunks

    def _format_pricing_data(self, pricing_data: List[PricingInfo]) -> str:
        formatted_lines = []

        for pricing in pricing_data:
            line_parts = []
            if pricing.product and pricing.product != "general":
                line_parts.append(f"Product: {pricing.product}")

            line_parts.append(f"Payment: {pricing.payment_method}")
            line_parts.append(f"Rate: {pricing.rate}")

            if pricing.volume_tier:
                line_parts.append(f"Volume: {pricing.volume_tier}")

            formatted_lines.append(" | ".join(line_parts))

        return "\n".join(formatted_lines)

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        try:
            response = await self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            for script in soup(["script", "style"]):
                script.decompose()

            chunks = self.chunk_document_content(soup, url)

            content = {
                "url": url,
                "title": soup.title.string if soup.title else "",
                "text": soup.get_text(strip=True, separator=' '),
                "headings": [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])],
                "meta_description": "",
                "links": [],
                "chunks": chunks,
                "pricing_data": [chunk.pricing_data for chunk in chunks if chunk.pricing_data]
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
        async with self:
            tasks = [self.scrape_url(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid_results = []
            for result in results:
                if isinstance(result, dict) and "error" not in result:
                    valid_results.append(result)

            return valid_results