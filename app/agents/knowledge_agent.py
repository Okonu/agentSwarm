from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentResponse, AgentType, ToolCall
from app.core.llm_client import LLMClient
from app.tools.vector_store import VectorStore
from app.tools.web_search import WebSearchTool
from typing import Dict, Any, List
import logging
import json

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, vector_store: VectorStore):
        super().__init__("Enhanced_Knowledge", AgentType.KNOWLEDGE, llm_client)
        self.vector_store = vector_store
        self.web_search = WebSearchTool()

        self.system_prompt = """
You are an Enhanced Knowledge Agent specialized in providing detailed information about InfinitePay's products and services with advanced pricing intelligence. Always answer in english.

Your capabilities include:
1. Structured pricing data analysis and comparison
2. Volume-based rate explanations
3. Payment method specific information
4. Product feature comparisons
5. Accurate fee calculations and ranges

InfinitePay Products/Services:
- Maquininhas (card readers): Smart, Celular, Tap-to-Pay
- Payment solutions: PIX, Boleto, Link de Pagamento
- Business tools: PDV, Loja Online, Gestão de Cobrança
- Financial services: Conta Digital, Empréstimo, Cartão, Rendimento

Enhanced Instructions:
1. For pricing queries, provide specific rates when available
2. Explain volume tiers and conditions clearly
3. Compare different payment methods when relevant
4. Include rate ranges and conditions
5. Cite sources and provide context
6. If pricing data is incomplete, explain what's available vs missing
7. Respond in the same language as the user's question

Always prioritize accuracy and provide structured, detailed responses for pricing inquiries.
"""

    async def process(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        try:
            tool_calls = []
            response_parts = []

            query_analysis = self._analyze_query(message)

            try:
                search_type = "pricing" if query_analysis["is_pricing_query"] else "all"
                rag_results = await self.vector_store.search_enhanced(
                    message,
                    k=5,
                    search_type=search_type
                )

                if rag_results:
                    pricing_insights = self.vector_store.extract_pricing_insights(message, rag_results)
                    enhanced_context = self._build_enhanced_context(
                        rag_results,
                        pricing_insights,
                        query_analysis
                    )

                    tool_calls.append(ToolCall(
                        tool_name="enhanced_rag_retrieval",
                        tool_input={
                            "query": message,
                            "search_type": search_type,
                            "query_analysis": query_analysis
                        },
                        tool_output={
                            "results_count": len(rag_results),
                            "top_similarity": rag_results[0]['similarity'] if rag_results else 0,
                            "has_pricing_data": pricing_insights["has_pricing_data"],
                            "payment_methods_found": list(pricing_insights["payment_methods"]),
                            "rate_ranges": pricing_insights["rate_ranges"]
                        }
                    ))

                    enhanced_response = await self._generate_enhanced_response(
                        message, enhanced_context, pricing_insights, query_analysis
                    )
                    response_parts.append(enhanced_response)

            except Exception as e:
                logger.error(f"Error in enhanced RAG retrieval: {str(e)}")

            if not response_parts or not query_analysis["is_infinitepay_specific"]:
                try:
                    search_results = await self.web_search.search(message, max_results=3)

                    if search_results and not search_results[0].get("error"):
                        web_response = await self._generate_web_search_response(
                            message, search_results
                        )
                        response_parts.append(web_response)

                        tool_calls.append(ToolCall(
                            tool_name="web_search",
                            tool_input={"query": message},
                            tool_output={"results_count": len(search_results)}
                        ))

                except Exception as e:
                    logger.error(f"Error in web search: {str(e)}")

            if not response_parts:
                response_parts.append(
                    "I apologize, but I'm having trouble accessing information sources right now. "
                    "Could you please rephrase your question or try again later?"
                )

            final_response = "\n\n".join(response_parts)

            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response=final_response,
                tool_calls=tool_calls,
                confidence=0.9 if tool_calls else 0.3,
                metadata={
                    "query_analysis": query_analysis,
                    "sources_count": len(tool_calls),
                    "enhanced_features_used": True
                }
            )

        except Exception as e:
            logger.error(f"Error in enhanced knowledge agent: {str(e)}")
            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response="I'm sorry, I encountered an error while processing your request. Please try again.",
                tool_calls=[],
                confidence=0.0,
                metadata={"error": str(e)}
            )

    def _analyze_query(self, message: str) -> Dict[str, Any]:
        message_lower = message.lower()

        is_pricing_query = any(keyword in message_lower for keyword in [
            'fee', 'rate', 'cost', 'price', 'charge', '%', 'percent', 'how much',
            'quanto custa', 'taxa', 'preço', 'valor'
        ])

        is_comparison_query = any(keyword in message_lower for keyword in [
            'compare', 'difference', 'vs', 'versus', 'better', 'best',
            'comparar', 'diferença', 'melhor'
        ])

        is_infinitepay_specific = any(keyword in message_lower for keyword in [
            'infinitepay', 'maquininha', 'maquinha', 'smart', 'celular',
            'tap-to-pay', 'pix', 'boleto', 'conta digital'
        ])

        mentioned_products = []
        product_keywords = {
            'maquininha_smart': ['maquininha smart', 'smart machine'],
            'infinitetap': ['infinitetap', 'celular', 'phone machine'],
            'payment_link': ['payment link', 'link de pagamento'],
            'pix': ['pix'],
            'digital_account': ['conta digital', 'digital account']
        }

        for product, keywords in product_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                mentioned_products.append(product)

        return {
            "is_pricing_query": is_pricing_query,
            "is_comparison_query": is_comparison_query,
            "is_infinitepay_specific": is_infinitepay_specific,
            "mentioned_products": mentioned_products,
            "query_complexity": "high" if (
                        is_pricing_query and is_comparison_query) else "medium" if is_pricing_query else "low"
        }

    def _build_enhanced_context(self, rag_results: List[Dict], pricing_insights: Dict, query_analysis: Dict) -> str:
        context_parts = []

        if pricing_insights["has_pricing_data"]:
            context_parts.append("=== PRICING INFORMATION ===")

            if pricing_insights["rate_ranges"]:
                context_parts.append("Rate Ranges by Payment Method:")
                for method, rates in pricing_insights["rate_ranges"].items():
                    if rates["min"] == rates["max"]:
                        context_parts.append(f"• {method.title()}: {rates['min']}%")
                    else:
                        context_parts.append(f"• {method.title()}: {rates['min']}% - {rates['max']}%")

            if pricing_insights["specific_rates"]:
                context_parts.append("\nDetailed Pricing:")
                for rate_info in pricing_insights["specific_rates"][:5]:
                    rate_line = f"• {rate_info['payment_method'].title()}: {rate_info['rate']}"
                    if rate_info["volume_tier"]:
                        rate_line += f" (Volume: {rate_info['volume_tier']})"
                    context_parts.append(rate_line)

            if pricing_insights["volume_tiers"]:
                context_parts.append(f"\nVolume Tiers Available: {', '.join(pricing_insights['volume_tiers'])}")

        context_parts.append("\n=== RETRIEVED CONTENT ===")
        for i, result in enumerate(rag_results[:3]):
            context_parts.append(f"\nSource {i + 1} (Similarity: {result['similarity']:.2f}):")
            context_parts.append(f"URL: {result['metadata']['url']}")
            context_parts.append(f"Content: {result['document'][:400]}...")

            if result.get("chunk_type"):
                context_parts.append(f"Content Type: {result['chunk_type']}")

        return "\n".join(context_parts)

    async def _generate_enhanced_response(self, query: str, enhanced_context: str, pricing_insights: Dict,
                                          query_analysis: Dict) -> str:

        if query_analysis["is_pricing_query"]:
            prompt_template = """
Based on the following InfinitePay pricing information, provide a comprehensive answer about fees and rates.

{enhanced_context}

User Question: {query}

Instructions:
1. Provide specific rates when available
2. Explain any volume-based pricing tiers
3. Compare different payment methods if relevant
4. Mention any conditions or limitations
5. If specific rates aren't available, explain what information is provided
6. Be precise and cite sources

Provide a detailed, accurate response focusing on pricing information.
"""
        else:
            prompt_template = """
Based on the following InfinitePay information, answer the user's question comprehensively.

{enhanced_context}

User Question: {query}

Provide a helpful, accurate answer based on the retrieved content. Include specific details when available.
"""

        formatted_prompt = prompt_template.format(
            enhanced_context=enhanced_context,
            query=query
        )

        return await self.llm_client.generate_response_with_system_prompt(
            self.system_prompt,
            formatted_prompt
        )

    async def _generate_web_search_response(self, query: str, search_results: List[Dict]) -> str:
        search_context = []
        for result in search_results:
            search_context.append(f"""
Title: {result.get('title', 'N/A')}
Snippet: {result.get('snippet', 'N/A')}
Source: {result.get('source', 'Web Search')}
""")

        web_context = "\n".join(search_context)

        web_prompt = f"""
Based on the following web search results, answer the user's question.

Search Results:
{web_context}

User Question: {query}

Provide a helpful answer based on the search results.
"""

        return await self.llm_client.generate_response_with_system_prompt(
            self.system_prompt,
            web_prompt
        )