# Agent Swarm API

A multi-agent system that processes user requests through specialized AI agents working together to provide intelligent responses.

## 🏗️ Architecture

The system consists of four main agents that collaborate to handle user queries:

### **Router Agent**
- **Purpose**: Analyzes incoming messages and routes them to the appropriate specialized agent
- **File**: `app/agents/router_agent.py`
- **Function**: Determines whether a query needs knowledge retrieval or customer support

### **Knowledge Agent** 
- **Purpose**: Handles information retrieval using RAG (Retrieval Augmented Generation) and web search
- **File**: `app/agents/knowledge_agent.py`
- **Features**: 
  - RAG system for InfinitePay product information
  - Web search for general queries
  - Enhanced pricing intelligence

### **Support Agent**
- **Purpose**: Provides customer support with access to customer data and tools
- **File**: `app/agents/support_agent.py`
- **Tools**:
  - Customer information retrieval
  - Account status checking
  - Transaction history access

### **Personality Agent**
- **Purpose**: Adds human-like personality and warmth to responses
- **File**: `app/agents/personality_agent.py`
- **Function**: Transforms technical responses into friendly, conversational ones

## 📋 Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API Key

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd agent-swarm
```

### 2. Environment Configuration
```bash
# Create environment file
cp .env.example .env

# Edit with your OpenAI API key
nano .env
```

**Required in .env:**
```env
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
VECTOR_STORE_PATH=/app/data/vector_store
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### 3. Run with Docker (Recommended)
```bash
# Build and start the application
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 4. Manual Setup (Alternative)
```bash
# Install dependencies
pip install -r requirements.txt

# Create data directory
mkdir -p data/vector_store

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 API Usage

### Chat Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the fees for Maquininha Smart?",
    "user_id": "client789"
  }'
```

### Example Response
```json
{
  "response": "I'd be happy to help! The Maquininha Smart has competitive rates starting at 2.5% for credit card transactions.",
  "source_agent_response": "Maquininha Smart fees: Credit cards 2.5%, Debit cards 1.9%, PIX free",
  "agent_workflow": [
    {
      "agent_name": "Router",
      "tool_calls": {
        "route_analysis": {
          "agent": "KNOWLEDGE",
          "reasoning": "Product pricing inquiry"
        }
      }
    },
    {
      "agent_name": "Knowledge", 
      "tool_calls": {
        "rag_retrieval": {
          "results_count": 3
        }
      }
    },
    {
      "agent_name": "Personality",
      "tool_calls": {
        "personality_enhancement": true
      }
    }
  ]
}
```

### Health Check
```bash
curl http://localhost:8000/health
```

## 🧪 Testing

### Run All Tests
```bash
# Using pytest
pytest -v

# Specific test files
pytest test_agents.py -v
pytest test_api.py -v
pytest test_tools.py -v
```

### Test Categories
- **Agent Tests** (`test_agents.py`): Individual agent functionality
- **API Tests** (`test_api.py`): HTTP endpoint testing  
- **Tools Tests** (`test_tools.py`): Web scraping and customer tools

## 📁 Project Structure

```
agentSwarm/
├── app/
│   ├── agents/
│   │   ├── base_agent.py          # Base agent class
│   │   ├── router_agent.py        # Message routing
│   │   ├── knowledge_agent.py     # Information retrieval
│   │   ├── support_agent.py       # Customer support
│   │   └── personality_agent.py   # Response enhancement
│   ├── core/
│   │   ├── config.py              # Configuration settings
│   │   ├── llm_client.py          # OpenAI integration
│   │   └── communication.py       # Agent communication
│   ├── tools/
│   │   ├── web_search.py          # DuckDuckGo search
│   │   ├── web_scraper.py         # Content scraping
│   │   ├── vector_store.py        # ChromaDB integration
│   │   └── customer_tools.py      # Customer data tools
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   └── main.py                    # FastAPI application
├── tests/
│   ├── test_agents.py             # Agent unit tests
│   ├── test_api.py                # API endpoint tests
│   └── test_tools.py              # Tool functionality tests
├── docker-compose.yml             # Docker setup
├── Dockerfile                     # Container definition
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## 🔧 Key Features

### RAG System
- **Vector Store**: ChromaDB with sentence transformers
- **Data Sources**: InfinitePay website content (18+ URLs)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Collections**: Text, pricing, and structured data

### Web Search
- **Provider**: DuckDuckGo (no API key required)
- **Fallback**: For general queries not in knowledge base
- **Integration**: Seamless switching between RAG and web search

### Customer Support Tools
- **Customer Data Tool**: User information and account status
- **Transaction Tool**: Recent transaction history
- **Mock Data**: Realistic customer scenarios for testing

### Pricing Intelligence
- **Advanced Extraction**: Regex patterns for pricing information
- **Multi-format Support**: Percentages, currencies, ranges
- **Structured Output**: Organized pricing data with metadata

## 🌐 Example Queries

### Product Information
```json
{
  "message": "What are the fees for Maquininha Smart?",
  "user_id": "client789"
}
```

### Customer Support
```json
{
  "message": "I can't make transfers from my account",
  "user_id": "client789"  
}
```

### General Information
```json
{
  "message": "Quando foi o último jogo do Palmeiras?",
  "user_id": "client789"
}
```

### Multi-language Support
```json
{
  "message": "How can I use my phone as a card machine?",
  "user_id": "client789"
}
```

## 🔍 How It Works

### 1. **Message Processing Flow**
```
User Query → Router Agent → Specialized Agent → Personality Agent → Response
```

### 2. **Knowledge Agent Decision Tree**
```
InfinitePay Query? → RAG Search → Vector Store Results
General Query? → Web Search → DuckDuckGo Results  
```

### 3. **Support Agent Workflow**
```
Support Query → Customer Tools → Account Check → Personalized Response
```

### 4. **Response Enhancement**
```
Technical Response → Personality Agent → Human-like Response
```

## 🛠️ Configuration Options

### Environment Variables
```env
# Core Configuration
OPENAI_API_KEY=required
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7

# Vector Store
VECTOR_STORE_PATH=/app/data/vector_store
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# API Settings
API_V1_STR=/api/v1
PROJECT_NAME=Agent Swarm API
```

### InfinitePay Data Sources
The system automatically scrapes and indexes content from:
- https://www.infinitepay.io
- https://www.infinitepay.io/maquininha
- https://www.infinitepay.io/maquininha-celular
- https://www.infinitepay.io/tap-to-pay
- https://www.infinitepay.io/pdv
- [... and 13 more URLs]

## 🐳 Docker Configuration

### docker-compose.yml
```yaml
version: '3.8'
services:
  agent-swarm:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LLM_MODEL=gpt-3.5-turbo
      - LLM_TEMPERATURE=0.7
      - VECTOR_STORE_PATH=/app/data/vector_store
      - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    volumes:
      - vector_data:/app/data/vector_store
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## 📊 Monitoring

### Health Check Endpoint
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "initialized": true,
  "vector_store_info": {
    "text_documents": 45,
    "pricing_documents": 12,
    "structured_documents": 28,
    "document_count": 85
  }
}
```

### Index Management
```bash
# Rebuild vector store index
POST /api/v1/rebuild-index
```

## 🔧 Troubleshooting

### Common Issues

**1. Vector Store Not Initializing**
```bash
# Check data directory permissions
ls -la ./data/vector_store/

# Recreate directory
rm -rf ./data/vector_store
mkdir -p ./data/vector_store
```

**2. OpenAI API Issues**
```bash
# Verify API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**3. Web Scraping Failures**
```bash
# Test DuckDuckGo connectivity
curl "https://api.duckduckgo.com/?q=test&format=json"

# Check logs for scraping errors
docker-compose logs agent-swarm
```

**4. Port Already in Use**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
docker-compose up -p 8001:8000
```

## 🧪 Testing Strategy

### Unit Tests
- **Router Agent**: Message routing logic
- **Knowledge Agent**: RAG and web search functionality  
- **Support Agent**: Customer tool integration
- **Personality Agent**: Response enhancement

### Integration Tests
- **API Endpoints**: Full request/response cycle
- **Agent Communication**: Multi-agent workflows
- **Error Handling**: Graceful failure scenarios

### Test Data
- Mock customer data for support scenarios
- Sample InfinitePay product queries
- General knowledge test cases

## 🚀 Production Deployment

### Environment Setup
```bash
# Production environment variables
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
ALLOWED_HOSTS=your-domain.com
CORS_ORIGINS=https://your-frontend.com
```

### Performance Considerations
- **Vector Store**: Consider external ChromaDB for scaling
- **Caching**: Implement Redis for response caching
- **Load Balancing**: Multiple container instances
- **Monitoring**: Add logging aggregation and metrics

## 📚 Dependencies

### Core Dependencies
- **FastAPI**: Web framework
- **OpenAI**: LLM integration
- **ChromaDB**: Vector database
- **LangChain**: LLM application framework
- **BeautifulSoup**: Web scraping
- **Sentence Transformers**: Text embeddings

### Development Dependencies  
- **Pytest**: Testing framework
- **HTTPX**: Async HTTP client for testing
- **Uvicorn**: ASGI server

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest -v

# Code formatting (if using)
black app/
```

### Adding New Agents
1. Inherit from `BaseAgent` class
2. Implement `process()` method
3. Register with `AgentCommunicationHub`
4. Add routing logic to `RouterAgent`
5. Write comprehensive tests

### Adding New Tools
1. Create tool class in `app/tools/`
2. Add async methods for tool operations
3. Integrate with appropriate agent
4. Add tool-specific tests

## 📄 License

This project is licensed under the MIT License.

---

**Agent Swarm API** - A production-ready multi-agent system for intelligent customer service and information retrieval.