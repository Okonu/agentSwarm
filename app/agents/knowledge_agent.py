from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentResponse, AgentType, ToolCall
from app.core.llm_client import LLMClient
from app.tools.vector_store import VectorStore
from app.tools.web_search import WebSearchTool
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, vector_store: VectorStore):
        super().__init__("Knowledge", AgentType.KNOWLEDGE, llm_client)
        self.vector_store = vector_store
        self.web_search = WebSearchTool()

        self.system_prompt = """
You are a Knowledge Agent specialized in providing information about InfinitePay's products and services.

Your primary sources of information:
1. InfinitePay's website content (via RAG retrieval)
2. Web search for general questions

InfinitePay Products/Services:
- Maquininhas (card readers): Smart, Celular, Tap-to-Pay
- Payment solutions: PIX, Boleto, Link de Pagamento
- Business tools: PDV, Loja Online, Gestão de Cobrança
- Financial services: Conta Digital, Empréstimo, Cartão, Rendimento

Instructions:
1. For InfinitePay-related questions, use the retrieved context first
2. For general questions, use web search
3. Always cite your sources
4. Provide accurate, helpful information
5. If you don't have specific information, say so clearly
6. Respond in the same language as the user's question

Be conversational but professional. Focus on being helpful and accurate.
"""

    async def process(self, message: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process knowledge queries using RAG and web search"""
        try:
            tool_calls = []
            response_parts = []

            infinitepay_keywords = [
                'infinitepay', 'maquininha', 'maquinha', 'smart', 'celular',
                'tap-to-pay', 'pix', 'boleto', 'conta digital', 'emprestimo',
                'cartao', 'rendimento', 'pdv', 'loja online', 'taxa', 'fee'
            ]

            is_infinitepay_query = any(keyword in message.lower() for keyword in infinitepay_keywords)

            if is_infinitepay_query:
                try:
                    rag_results = await self.vector_store.search(message, k=3)

                    if rag_results:
                        context_docs = []
                        for result in rag_results:
                            context_docs.append(f"""
Source: {result['metadata']['url']}
Title: {result['metadata']['title']}
Content: {result['document'][:500]}...
Similarity: {result['similarity']:.2f}
""")

                        rag_context = "\n".join(context_docs)

                        tool_calls.append(ToolCall(
                            tool_name="rag_retrieval",
                            tool_input={"query": message},
                            tool_output={"results_count": len(rag_results),
                                         "top_similarity": rag_results[0]['similarity']}
                        ))

                        rag_prompt = f"""
Based on the following InfinitePay website content, answer the user's question.

Retrieved Content:
{rag_context}

User Question: {message}

Provide a helpful, accurate answer based on the retrieved content. If the content doesn't fully answer the question, say so and provide what information you can.
"""

                        rag_response = await self.llm_client.generate_response_with_system_prompt(
                            self.system_prompt,
                            rag_prompt
                        )
                        response_parts.append(rag_response)

                except Exception as e:
                    logger.error(f"Error in RAG retrieval: {str(e)}")

            if not response_parts or not is_infinitepay_query:
                try:
                    search_results = await self.web_search.search(message, max_results=3)

                    if search_results and not search_results[0].get("error"):
                        search_context = []
                        for result in search_results:
                            search_context.append(f"""
Title: {result.get('title', 'N/A')}
Snippet: {result.get('snippet', 'N/A')}
Source: {result.get('source', 'Web Search')}
""")

                        web_context = "\n".join(search_context)

                        tool_calls.append(ToolCall(
                            tool_name="web_search",
                            tool_input={"query": message},
                            tool_output={"results_count": len(search_results)}
                        ))

                        web_prompt = f"""
Based on the following web search results, answer the user's question.

Search Results:
{web_context}

User Question: {message}

Provide a helpful answer based on the search results.
"""

                        web_response = await self.llm_client.generate_response_with_system_prompt(
                            self.system_prompt,
                            web_prompt
                        )
                        response_parts.append(web_response)

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
                confidence=0.8 if tool_calls else 0.3,
                metadata={"used_rag": is_infinitepay_query, "sources_count": len(tool_calls)}
            )

        except Exception as e:
            logger.error(f"Error in knowledge agent: {str(e)}")
            return AgentResponse(
                agent_name=self.name,
                agent_type=self.agent_type,
                response="I'm sorry, I encountered an error while processing your request. Please try again.",
                tool_calls=[],
                confidence=0.0,
                metadata={"error": str(e)}
            )