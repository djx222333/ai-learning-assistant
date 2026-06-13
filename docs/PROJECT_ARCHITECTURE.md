# Project Architecture

## System Architecture

`mermaid
flowchart TB
    subgraph Frontend[\"Frontend (Vercel)\"]
        React[\"React 19 + Vite 8\"]
        Tailwind[\"Tailwind CSS v4\"]
        AuthGuard[\"AuthGuard\"]
        Pages[\"Pages: Chat, Knowledge, Plans...\"]
    end

    subgraph Backend[\"Backend (Railway)\"]
        FastAPI[\"FastAPI\"]
        JWT[\"JWT Auth\"]
        ChatSvc[\"Chat Service\"]
        RAG[\"RAG Service\"]
        AgentAdapter[\"Agent Adapter\"]
    end

    subgraph Agents[\"LangGraph Agents\"]
        Supervisor[\"Supervisor Node\"]
        Router[\"Conditional Edge\"]
        CodeAgent[\"Code Agent\"]
        SearchAgent[\"Search Agent\"]
        CareerAgent[\"Career Agent\"]
        RAGAgent[\"RAG Agent\"]
        Planner[\"Planner Node\"]
    end

    subgraph Storage[\"Storage\"]
        PG[\"PostgreSQL\"]
        Redis[\"Redis (cache)\"]
        FAISS[\"FAISS Vector Index\"]
    end

    subgraph External[\"External\"]
        DS[\"DeepSeek API\"]
    end

    React -->|HTTP/REST| FastAPI
    FastAPI --> JWT
    FastAPI --> ChatSvc
    ChatSvc --> RAG
    RAG --> FAISS
    ChatSvc --> AgentAdapter
    AgentAdapter --> Supervisor
    Supervisor --> Router
    Router --> CodeAgent
    Router --> SearchAgent
    Router --> CareerAgent
    Router --> RAGAgent
    Router --> Planner
    CodeAgent --> DS
    SearchAgent --> DS
    CareerAgent --> DS
    RAGAgent --> RAG
    RAGAgent --> DS
    Planner --> DS
    ChatSvc --> PG
    FastAPI --> PG
    PG --> Redis
`

## Request Flow

### Chat Request

`
User types \"Python列表推导式是什么?\"
        │
        ▼
React Chat.tsx
        │  POST /api/v1/chat  { message, session_id }
        │  Authorization: Bearer <JWT>
        ▼
FastAPI chat.py
        │  Depends(get_current_user) → User isolation
        ▼
chat_service.py
        │  Step 1: RAG search (FAISS + embedding)
        ├── Found >= 0.4? → Augment message with context, source=\"rag\"
        └── Not found?    → Original message, source=\"llm\"
        │  Step 2: Call agent_adapter
        ▼
agent_adapter.py
        │  Reads config from config.py → sets env vars
        │  Calls graph.invoke({ messages, next_agent })
        ▼
supervisor_agent/agent_graph.py
        │  1. supervisor_node: LLM classifies question
        │     → code / english / career / search / research / rag / planner
        │  2. route_to_agent: Conditional Edge routes
        │  3. Sub-agent: create_react_agent with tools
        │  4. Agent calls DeepSeek API (or tools first)
        ▼
DeepSeek API
        │  model=deepseek-chat
        │  api_key=DEEPSEEK_API_KEY
        ▼
Response flows back through each layer
        │
        ▼
User sees answer in Chat UI
`

## Agent Architecture

### Supervisor Node

The Supervisor is the orchestrator. It:

1. Receives the user message
2. Uses DeepSeek to classify the question
3. Returns a category (code/english/career/search/research/rag/planner)
4. Conditional Edge routes to the appropriate agent

### Sub-Agents

| Agent | Tools | Responsibility |
|-------|-------|----------------|
| Code Agent | calculator, read_file, read_profile, update_profile | Python tutoring |
| English Agent | read_file, read_profile, update_profile | English learning |
| Career Agent | read_file, read_profile, update_profile | Study planning |
| Search Agent | web_search | Real-time internet info |
| Research Agent | web_search, read_file | In-depth research |
| RAG Agent | ingest_pdf, rag_search | Document Q&A |
| Planner | (none) | Task decomposition |

## State Architecture

`
SupervisorState (extends MessagesState)
├── messages: list   ← Shared across all agents (add_messages reducer)
└── next_agent: str  ← Supervisor's routing decision
`

Each agent is a `create_react_agent` sub-graph, registered as a single node
in the parent `StateGraph`. Memory is shared via `MemorySaver` (thread_id=session_id).

## Configuration Architecture

`
web_app/backend/app/core/config.py  (Single Source of Truth)
        │
        ├── os.environ  (set by agent_adapter.py before importing)
        │       │
        │       ▼
        │   supervisor_agent/agent_graph.py  (os.getenv)
        │
        ├── FastAPI route handlers  (from app.core.config import settings)
        │
        └── Docker environment variables  (.env.production | docker-compose)
`

## RAG Architecture

`
Upload PDF
   │
   ▼
knowledge_service.upload_file()
   │  → Save to uploads/ (UUID filename)
   │  → Create Document record in PostgreSQL
   ▼
rag_service.ingest_pdf()
   │  → PyMuPDF extract text
   │  → Chunk by paragraph (~500 chars)
   │  → SentenceTransformer(all-MiniLM-L6-v2) → embeddings
   │  → FAISS IndexFlatL2 → vector index
   ▼
Chat Service
   │  → knowledge_service.search(query)
   │  → FAISS similarity search
   │  → Top-K chunks + metadata
   ▼
RAG Agent
   │  → Augment prompt with citations
   │  → DeepSeek answers with source attribution
   ▼
Response: { answer, source: \"rag\", citations }
`

## Data Model

`
users ──── conversations ──── messages
  │              │
  │              └── citations (JSON)
  │
  ├── documents ──── chunks
  │
  └── plans ──── tasks
`

### Key Tables

| Table | Key Fields | Purpose |
|-------|-----------|---------|
| users | id, username, email, hashed_password | Auth |
| conversations | id, session_id, user_id, title, message_count | Chat sessions |
| messages | id, conversation_id, role, content, agent_type, citations | Messages |
| documents | id, user_id, filename, index_status, chunk_count | Uploaded files |
| chunks | id, document_id, content, embedding_idx | Text chunks |
| plans | id, user_id, title, goal, total_tasks, completed_tasks | Learning plans |
| tasks | id, plan_id, title, status, week | Plan tasks |
