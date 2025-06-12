from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.models.schemas import MessageRequest, MessageResponse
from app.core.config import settings
from app.core.communication import AgentCommunicationHub
from app.core.llm_client import LLMClient
from app.agents.router_agent import RouterAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.support_agent import SupportAgent
from app.agents.personality_agent import PersonalityAgent
from app.tools.vector_store import VectorStore
from app.tools.web_scraper import WebScraper
from contextlib import asynccontextmanager
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentSwarmOrchestrator:

    def __init__(self):
        self.llm_client = LLMClient()
        self.vector_store = VectorStore(
            persist_directory=settings.VECTOR_STORE_PATH,
            embedding_model=settings.EMBEDDING_MODEL
        )
        self.communication_hub = AgentCommunicationHub()

        self.router_agent = RouterAgent(self.llm_client)
        self.knowledge_agent = KnowledgeAgent(self.llm_client, self.vector_store)
        self.support_agent = SupportAgent(self.llm_client)
        self.personality_agent = PersonalityAgent(self.llm_client)

        self.communication_hub.register_agent("router", self.router_agent)
        self.communication_hub.register_agent("knowledge", self.knowledge_agent)
        self.communication_hub.register_agent("support", self.support_agent)
        self.communication_hub.register_agent("personality", self.personality_agent)

        self.is_initialized = False

    async def initialize(self):
        if self.is_initialized:
            return

        try:
            collection_info = self.vector_store.get_collection_info()

            # Use the correct key name that matches VectorStore.get_collection_info()
            if collection_info["document_count"] == 0:
                logger.info("Vector store is empty, scraping InfinitePay website...")
                await self._scrape_and_index_content()
            else:
                logger.info(f"Vector store already contains {collection_info['document_count']} documents")

            self.is_initialized = True
            logger.info("Agent swarm orchestrator initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing orchestrator: {str(e)}")
            raise

    async def _scrape_and_index_content(self):
        try:
            scraper = WebScraper()
            documents = await scraper.scrape_multiple_urls(settings.INFINITEPAY_URLS)

            if documents:
                # Use the correct method name from VectorStore
                await self.vector_store.add_documents_enhanced(documents)
                logger.info(f"Successfully indexed {len(documents)} documents")
            else:
                logger.warning("No documents were scraped")

        except Exception as e:
            logger.error(f"Error scraping and indexing content: {str(e)}")

    async def process_message(self, message: str, user_id: str) -> MessageResponse:
        try:
            self.communication_hub.reset_workflow()

            logger.info(f"Processing message for user {user_id}: {message[:50]}...")

            routing_response = await self.router_agent.process(message)
            target_agent = routing_response.metadata.get("agent", "KNOWLEDGE").lower()

            context = {
                "user_id": user_id,
                "routing_info": routing_response.metadata
            }

            if target_agent == "knowledge":
                agent_response = await self.knowledge_agent.process(message, context)
            elif target_agent == "support":
                agent_response = await self.support_agent.process(message, context)
            else:
                agent_response = await self.knowledge_agent.process(message, context)

            personality_context = {
                "source_response": agent_response.response,
                "original_query": message,
                "source_agent": agent_response.agent_name
            }

            personality_response = await self.personality_agent.process(
                message,
                personality_context
            )

            workflow = self.communication_hub.get_workflow_log()

            workflow.insert(0, {
                "agent_name": routing_response.agent_name,
                "tool_calls": {tc.tool_name: tc.tool_output for tc in routing_response.tool_calls}
            })

            workflow.append({
                "agent_name": agent_response.agent_name,
                "tool_calls": {tc.tool_name: tc.tool_output for tc in agent_response.tool_calls}
            })

            workflow.append({
                "agent_name": personality_response.agent_name,
                "tool_calls": {tc.tool_name: tc.tool_output for tc in personality_response.tool_calls}
            })

            return MessageResponse(
                response=personality_response.response,
                source_agent_response=agent_response.response,
                agent_workflow=workflow
            )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return MessageResponse(
                response="I apologize, but I encountered an error while processing your request. Please try again later.",
                source_agent_response="Error occurred during processing",
                agent_workflow=[{
                    "agent_name": "error_handler",
                    "tool_calls": {"error": str(e)}
                }]
            )

orchestrator = AgentSwarmOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Agent Swarm API...")
    await orchestrator.initialize()
    yield
    logger.info("Shutting down Agent Swarm API...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Agent Swarm API is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "initialized": orchestrator.is_initialized,
        "vector_store_info": orchestrator.vector_store.get_collection_info()
    }


@app.post(f"{settings.API_V1_STR}/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    try:
        if not orchestrator.is_initialized:
            await orchestrator.initialize()

        response = await orchestrator.process_message(request.message, request.user_id)
        return response

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(f"{settings.API_V1_STR}/rebuild-index")
async def rebuild_index(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(orchestrator._scrape_and_index_content)
        return {"message": "Index rebuild started in background"}
    except Exception as e:
        logger.error(f"Error starting index rebuild: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start index rebuild")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)