# LegalBuddy — Enterprise AI-Powered Legal Assistant

> Conversational legal guidance for India, powered by Corrective RAG (CRAG), LangGraph, and Llama 3.1.

[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple)](https://langchain-ai.github.io/langgraph/)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-blue)](https://www.pinecone.io/)
[![Upstash](https://img.shields.io/badge/Upstash-Semantic_Cache-00E676)](https://upstash.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://www.docker.com/)

---

##  Table of Contents

- [Overview](#overview)
- [System Architecture & Flow Graph](#system-architecture--flow-graph)
- [How the CRAG Engine Works](#how-the-crag-engine-works)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [API Reference](#api-reference)
- [Contributors](#contributors)

---

##  Overview

**LegalBuddy** is an advanced, decoupled AI legal assistant designed to make complex Indian statutory frameworks and legal procedures accessible to everyone. 

Unlike standard LLMs that are prone to hallucinating legal facts, LegalBuddy utilizes a **Corrective Retrieval-Augmented Generation (CRAG)** pipeline orchestrated by **LangGraph**. It actively grades the relevance of retrieved statutes, falls back to live web searches when local knowledge is insufficient, and streams tokens in real-time to a modern Next.js workspace.

**Target Audience:**
- Citizens seeking to understand their legal rights.
- Law students and researchers requiring fast, context-grounded statutory references.
- NGOs involved in legal awareness programs.

---

##  System Architecture & Flow Graph

LegalBuddy's architecture is divided into a high-performance **Next.js Client** and a **FastAPI/LangGraph Backend Engine**. 

Below is the state-machine workflow that executes every time a user submits a query:

```mermaid
graph TD
    %% Define Styles
    classDef user fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff
    classDef router fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#fff
    classDef db fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff
    classDef action fill:#7c2d12,stroke:#fb923c,stroke-width:2px,color:#fff
    classDef final fill:#14532d,stroke:#4ade80,stroke-width:2px,color:#fff

    User((User Input)):::user --> UI[Next.js Frontend Workspace]:::user
    UI -->|HTTP Chunked Stream| API(FastAPI /chat Endpoint):::action
    
    API --> LH[Load Chat History]:::router
    LH --> Router{Supervisor Router}:::router
    
    %% Intent Branches
    Router -->|Greeting| G[Handle Greeting]:::action
    Router -->|Out of Scope| OOS[Boundary Guardrail]:::action
    Router -->|Clarification| Clarify[Rewrite Past Answer]:::action
    Router -->|Legal Search| QR[Query Rewriter]:::action
    
    %% Legal Search Flow
    QR --> Cache{Check Upstash Semantic Cache}:::db
    
    Cache -->|Cache Hit| Gen[Synthesize Final Answer]:::final
    Cache -->|Cache Miss| Retrieve[Retrieve from Pinecone Vector DB]:::db
    
    Retrieve --> Grade
    
    %% Grading Logic
    Grade -->|Relevance >= 3| Gen
    Grade -->|Relevance < 3| Web[Tavily Corrective Web Search]:::action
    
    Web --> Gen
    
    %% Output
    Gen --> Stream[Stream Tokens via Llama 3.1]:::final
    G --> Stream
    OOS --> Stream
    Clarify --> Stream
    
    Stream -.->|Real-Time TextDecoder| UI

```

---

##  How the CRAG Engine Works

The backend utilizes a sophisticated multi-agent state graph. Key nodes include:

1. **Supervisor Router**: An LLM-based classifier that intercepts user queries and categorizes them into `greeting`, `out_of_scope`, `clarification`, or `legal_search`. This prevents injection attacks and keeps the bot focused on law.
2. **Query Rewriter**: Resolves pronouns and contextual gaps from the chat history (e.g., transforming "What is the penalty for it?" into "What is the penalty for wire fraud under Indian Law?").
3. **Semantic Cache (Upstash)**: Checks a high-speed vector index for exact historical query matches (Cosine similarity > 0.98). A cache hit bypasses heavy retrieval steps, saving time and API costs.
4. **Pinecone Retrieval**: Pulls the top semantic matches from separate local `text` (PDF) and `json` namespaces.
5. **Likert Document Grader**: An LLM evaluates retrieved chunks on a strict 1-5 Likert scale. If all chunks score below 3, the system rejects the local data.
6. **Corrective Web Search (Tavily)**: Triggered only if local documents fail the grading threshold, pulling live, up-to-date legal precedent from verified domains like *indiankanoon.org*.

---

##  Tech Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| **Frontend UI** | Next.js 14, Tailwind CSS | Decoupled client, App Router, responsive design |
| **Backend API** | FastAPI, Uvicorn | Asynchronous REST endpoints, HTTP Chunked Streaming |
| **Orchestration** | LangGraph | Multi-agent state machine, conditional routing |
| **LLM Inference** | Llama 3.1 8B (via Groq) | Ultra-low latency generation and structural grading |
| **Embeddings** | FastEmbed (BAAI/bge-small) | Mathematical semantic mapping |
| **Vector DB** | Pinecone | Cloud-hosted dense statutory knowledge base |
| **Cache Layer** | Upstash Vector | Sub-millisecond semantic query caching |
| **Relational DB** | NeonDB (PostgreSQL) | Secure user credential and session thread storage |

---

##  Project Structure

```text
LegalBuddy/
├── app/                      # FastAPI Server & Request Routers
│   └── main.py               # Core App and Streaming Endpoints
├── src/                      # ML Logic & Specialized RAG Subsystems
│   ├── chat_history.py       # Relational Logging to NeonDB
│   ├── data_loader.py        # PDF Parsing & Chunk Preprocessing
│   ├── embedding.py          # Vector Mapping Definitions
│   ├── llm.py                # Core Inference Engine Bindings
│   ├── rag_pipeline.py       # LangGraph Workflows & Context Routing
│   └── vector_store.py       # Pinecone Upsert & Initialization
├── frontend/                 # Decoupled Next.js Web Workspace
│   ├── app/                  # Next.js App Router & Layouts
│   ├── components/           # UI Elements (AuthForm, Sidebar, ChatWindow)
│   ├── Dockerfile.frontend   # Node Environment Build Manifest
│   └── tailwind.config.ts    # Custom UI Styling Tokens
├── Dockerfile                # Backend Service Build Manifest
├── docker-compose.yml        # Multi-Container Orchestration Blueprint
└── render.yaml               # Managed Infrastructure Deployment Pipeline

```

---

##  Setup & Installation

### 1. Environment Variables

Duplicate the `.env.example` file in the root directory and rename it to `.env`. Populate it with your credentials:

```env
PINECONE_API_KEY=your_pinecone_api_key_here
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
DATABASE_URL=postgresql://<user>:<password>@<host>/<dbname>?sslmode=require
UPSTASH_VECTOR_REST_URL=[https://your-index-name.upstash.io](https://your-index-name.upstash.io)
UPSTASH_VECTOR_REST_TOKEN=your_upstash_rest_token_here
NEXT_PUBLIC_API_URL=http://localhost:8000

```

### 2. Docker Execution (Recommended)

Launch the fully decoupled stack (Next.js + FastAPI) inside isolated containers:

```bash
docker-compose up --build

```

* **Frontend**: Accessible at `http://localhost:3000`
* **Backend**: Accessible at `http://localhost:8000`

### 3. Manual Local Execution

If you prefer running the services without Docker:

**Terminal 1 (Backend):**

```bash
python -m venv venv
source venv/bin/activate  # Or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

```

**Terminal 2 (Frontend):**

```bash
cd frontend
npm install
npm run dev

```

---

## API Reference

### 1. Account Creation

* **Endpoint:** `POST /register`
* **Payload:** `{ "username": "user123", "password": "secure_password" }`

### 2. Session Validation

* **Endpoint:** `POST /login`
* **Payload:** `{ "username": "user123", "password": "secure_password" }`

### 3. Contextual RAG Stream

* **Endpoint:** `POST /chat`
* **Payload:** `{ "query": "What are the grounds for divorce?", "user_id": "user123", "session_id": "uuid-here" }`
* **Response Protocol:** `text/plain` (Yields raw text tokens via HTTP Chunked Transfer Encoding for real-time frontend rendering).

---

##  Contributors

This repository is developed and contributed by **Surya Prakash Baid** and **Abhay Kumar Gupta**.

```

```
