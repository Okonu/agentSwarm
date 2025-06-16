# Agent Swarm API Documentation

Complete API reference for the Agent Swarm multi-agent system.

## Base URL

```
http://localhost:8000
```

## API Endpoints

### **Core Endpoints**


## 1. **Root Endpoint**

### `GET /`

Basic API information and status.

**Response:**
```json
{
  "message": "Agent Swarm API is running",
  "status": "healthy"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

## 2. **Health Check**

### `GET /health`

System health status and initialization state.

**Response Schema:**
```json
{
  "status": "healthy" | "unhealthy",
  "initialized": boolean,
  "vector_store_info": {
    "text_documents": number,
    "pricing_documents": number, 
    "structured_documents": number,
    "document_count": number,
    "collections": string[]
  },
  "timestamp": "ISO_8601_string"
}
```

**Example Request:**
```bash
curl http://localhost:8000/health
```

**Example Response:**
```json
{
  "status": "healthy",
  "initialized": true,
  "vector_store_info": {
    "text_documents": 45,
    "pricing_documents": 12,
    "structured_documents": 28,
    "document_count": 85,
    "collections": ["text", "pricing", "structured"]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 3. **Chat Endpoint** 

### `POST /api/v1/chat`

Main endpoint for processing user messages through the agent swarm.

**Request Schema:**
```json
{
  "message": "string",    // Required: User's message/question
  "user_id": "string"     // Required: Unique user identifier
}
```

**Response Schema:**
```json
{
  "response": "string",               // Final human-friendly response
  "source_agent_response": "string", // Original agent response before personality enhancement
  "agent_workflow": [                // Array of agent processing steps
    {
      "agent_name": "string",
      "tool_calls": {
        "tool_name": "tool_output"
      },
      "confidence": number,           // Optional: Agent confidence (0.0-1.0)
      "metadata": object              // Optional: Additional agent metadata
    }
  ]
}
```

### **Example Requests & Responses**

#### **Product Pricing Query**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the fees for Maquininha Smart?",
    "user_id": "client789"
  }'
```

**Response:**
```json
{
  "response": "I'd be happy to help! The Maquininha Smart has competitive rates starting at 2.5% for credit card transactions, with special rates for high-volume merchants.",
  "source_agent_response": "Maquininha Smart fees: Credit cards 2.5%, Debit cards 1.9%, PIX free",
  "agent_workflow": [
    {
      "agent_name": "Router",
      "tool_calls": {
        "route_analysis": {
          "agent": "KNOWLEDGE",
          "reasoning": "Product pricing inquiry",
          "priority": "medium",
          "context": {
            "user_intent": "product_pricing",
            "query_type": "pricing"
          }
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

#### **Customer Support Query**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I cannot make transfers from my account",
    "user_id": "client789"
  }'
```

**Response:**
```json
{
  "response": "I understand your concern about account transfers. Let me check your account status and help resolve this issue.",
  "source_agent_response": "Account status: active, no restrictions found. Transfer limits: daily R$ 5,000, monthly R$ 50,000",
  "agent_workflow": [
    {
      "agent_name": "Router",
      "tool_calls": {
        "route_analysis": {
          "agent": "SUPPORT",
          "reasoning": "Account access issue", 
          "priority": "high",
          "context": {
            "user_intent": "account_help",
            "query_type": "account_issue"
          }
        }
      }
    },
    {
      "agent_name": "Support",
      "tool_calls": {
        "get_customer_info": {
          "success": true
        },
        "check_account_status": {
          "success": true
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

#### **General Information Query**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quando foi o último jogo do Palmeiras?",
    "user_id": "client789"
  }'
```

**Response:**
```json
{
  "response": "Pelo que encontrei, o último jogo do Palmeiras foi ontem contra o Corinthians, com vitória por 2-1. Foi uma partida emocionante!",
  "source_agent_response": "Palmeiras last game: Yesterday vs Corinthians, won 2-1",
  "agent_workflow": [
    {
      "agent_name": "Router",
      "tool_calls": {
        "route_analysis": {
          "agent": "KNOWLEDGE",
          "reasoning": "General information query",
          "priority": "low"
        }
      }
    },
    {
      "agent_name": "Knowledge",
      "tool_calls": {
        "web_search": {
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

## 4. **Index Rebuild**

### `POST /api/v1/rebuild-index`

Rebuilds the vector store index by re-scraping InfinitePay website content.

**Request:** No body required

**Response:**
```json
{
  "message": "Index rebuild started in background"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/rebuild-index
```

**Note:** This operation runs in the background and may take several minutes to complete.


## 📊 Error Responses

### **Standard Error Format**

```json
{
  "error": "string",
  "details": "string",
  "timestamp": "string"
}
```

### **Common Error Codes**

#### **400 Bad Request**
```json
{
  "error": "HTTP 400", 
  "details": "Message cannot be empty"
}
```

#### **500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "details": "An unexpected error occurred. Please try again later."
}
```

#### **Graceful Chat Errors**
When the chat endpoint encounters errors, it returns a 200 status with an error response structure:

```json
{
  "response": "I apologize, but I encountered an error while processing your request. Please try again later.",
  "source_agent_response": "Error occurred during processing",
  "agent_workflow": [
    {
      "agent_name": "error_handler",
      "tool_calls": {
        "error": "Connection timeout"
      }
    }
  ]
}
```

## Agent Workflow Details

### **Router Agent Workflow**
The Router Agent analyzes incoming messages and determines routing:

**Tool Calls:**
- `route_analysis`: Determines target agent and reasoning

**Possible Routing Decisions:**
- `KNOWLEDGE`: Product info, pricing, general questions
- `SUPPORT`: Account issues, technical problems, user-specific queries

### **Knowledge Agent Workflow**
Handles information retrieval through multiple strategies:

**Tool Calls:**
- `rag_retrieval`: Search internal InfinitePay knowledge base
- `web_search`: Search external sources for general queries

**Decision Logic:**
- InfinitePay-specific queries → RAG system
- General queries → Web search
- Pricing queries → Enhanced pricing extraction

### **Support Agent Workflow**
Provides customer support with data access:

**Tool Calls:**
- `get_customer_info`: Retrieve customer profile data
- `check_account_status`: Verify account status and issues
- `get_recent_transactions`: Fetch recent transaction history

**Customer Context:**
- Customer found: Personalized support with account details
- Customer not found: General support guidance

### **Personality Agent Workflow**
Enhances responses with human-like personality:

**Tool Calls:**
- `personality_enhancement`: Transform technical responses to conversational

**Enhancement Features:**
- Friendly greetings and closings
- Empathetic language for problems
- Clear, easy-to-understand explanations
- Maintains all factual information

## Multi-Language Support

The system supports both English and Portuguese:

### **English Queries**
```json
{
  "message": "What are the fees for credit card processing?",
  "user_id": "user123"
}
```

### **Portuguese Queries**
```json
{
  "message": "Quais são as taxas para cartão de crédito?",
  "user_id": "user123"
}
```

**Response Language:** Matches the input language automatically.

## 📈 Response Metadata

### **Confidence Scores**
Some agents provide confidence scores (0.0 - 1.0):
- **Router Agent**: Routing decision confidence
- **Knowledge Agent**: Information retrieval confidence  
- **Support Agent**: Customer data match confidence

### **Processing Times**
Track agent performance through workflow timing:
```json
{
  "agent_name": "Knowledge",
  "tool_calls": {
    "rag_retrieval": {
      "results_count": 5,
      "processing_time_ms": 850
    }
  }
}
```

### **Tool Call Details**
Each tool call includes:
- **Tool Input**: Parameters passed to the tool
- **Tool Output**: Results and metadata from tool execution
- **Success Status**: Whether the tool executed successfully

## Query Types & Routing

### **Automatic Query Classification**

The Router Agent classifies queries into categories:

#### **Product/Pricing Queries** → Knowledge Agent
- "What are the fees for..."
- "How much does X cost?"
- "What are the rates for..."
- "Pricing information for..."

#### **Support Queries** → Support Agent  
- "I can't access my account"
- "My transfer failed"
- "Why can't I...?"
- "I'm having trouble with..."

#### **General Information** → Knowledge Agent + Web Search
- "What is PIX?"
- "Latest news about..."
- "When was..."
- "How to..."

## Development & Testing

### **API Testing with Different Tools**

#### **cURL Examples**
```bash
# Health check
curl http://localhost:8000/health

# Chat request
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "user_id": "test"}'

# Rebuild index
curl -X POST http://localhost:8000/api/v1/rebuild-index
```

#### **Python Requests**
```python
import requests

# Chat request
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "What are the fees for Maquininha Smart?",
        "user_id": "client789"
    }
)
print(response.json())
```

#### **JavaScript Fetch**
```javascript
// Chat request
const response = await fetch('http://localhost:8000/api/v1/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: "What are the fees for Maquininha Smart?",
    user_id: "client789"
  })
});

const data = await response.json();
console.log(data);
```

## Request Validation

### **Required Fields**
- `message`: Cannot be empty or whitespace only
- `user_id`: Cannot be empty or whitespace only

### **Field Limits**
- `message`: Maximum 10,000 characters (configurable)
- `user_id`: Maximum 255 characters

### **Validation Errors**
```json
{
  "error": "HTTP 400",
  "details": "Message cannot be empty"
}
```

```json
{
  "error": "HTTP 400", 
  "details": "User ID is required"
}
```

## Security Considerations

### **Rate Limiting**
- Default: 60 requests per minute per IP
- Configurable via environment variables

### **Input Sanitization**
- All inputs are validated and sanitized
- HTML content is escaped
- SQL injection protection (not applicable - no SQL database)

### **API Key Security**
- OpenAI API key stored in environment variables
- Not exposed in responses or logs

## 📊 Monitoring & Observability

### **Logging**
All requests are logged with:
- Timestamp
- User ID
- Message (truncated for privacy)
- Processing time
- Agent workflow
- Error details (if any)

### **Metrics**
Available metrics:
- Request count
- Response times  
- Error rates
- Agent usage statistics
- Vector store query performance

### **Health Monitoring**
Regular health checks monitor:
- API responsiveness
- Vector store connectivity
- OpenAI API connectivity
- Agent initialization status

