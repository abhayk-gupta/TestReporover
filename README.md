# LegalBuddy — AI-Powered Legal Assistant for India

> Conversational legal guidance powered by Corrective RAG (CRAG), LangGraph, and Llama 3.1.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-latest-orange)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-purple)](https://langchain-ai.github.io/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-latest-red)](https://www.trychroma.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://www.docker.com/)

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Architecture](#architecture)
- [How the CRAG Pipeline Works](#how-the-crag-pipeline-works)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Environment Variables](#environment-variables)
- [Docker Deployment](#docker-deployment)
- [Design Decisions](#design-decisions)

---

## Overview

**LegalBuddy** is an AI-powered legal assistant designed to make Indian legal information accessible to everyone — not just legal professionals. Users can ask questions in plain language and receive accurate, context-grounded responses based on actual legal documents and statutes.

Under the hood, LegalBuddy uses a **Corrective RAG (CRAG)** architecture orchestrated by **LangGraph**. Before generating any answer, the system retrieves relevant documents, grades their quality using an LLM-based scorer, and — if the local knowledge base falls short — automatically falls back to a live web search via Tavily. This multi-step verification process significantly reduces hallucinations, which is critical in a legal context where inaccurate information can cause real harm.

**Target users:**
- Citizens seeking to understand their legal rights and procedures
- NGOs and social workers involved in legal awareness programs
- Law students and researchers needing an interactive legal reference
- Individuals involved in or considering legal action who need preliminary guidance

---

## Problem Statement

Access to legal information in India remains a significant barrier for the general public. Legal documents — statutes, case law, procedural codes — are dense, jargon-heavy, and not designed for lay readers. Traditional legal search tools primarily serve professionals and are poorly suited for conversational, plain-language queries.

LegalBuddy addresses three core gaps:

1. **Accessibility** — Most people cannot interpret legal documents without professional help. LegalBuddy translates complex statutes into plain, empathetic language.
2. **Accuracy** — General-purpose LLMs frequently hallucinate legal facts. LegalBuddy uses CRAG to ground every response in retrieved, scored source documents.
3. **Context continuity** — Legal queries are rarely isolated. LegalBuddy maintains per-user, per-session chat history so follow-up questions are answered in context.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                     LangGraph CRAG Pipeline             │
│                                                         │
│  load_history → retrieve → grade_documents              │
│                                  │                      │
│                         ┌────────┴────────┐             │
│                     relevant?         not relevant?     │
│                         │                  │            │
│                       generate         web_search       │
│                         ▲                  │            │
│                         └──────────────────┘            │
│                                  │                      │
│                                 END                     │
└─────────────────────────────────────────────────────────┘
    │
    ▼
FastAPI Backend  ←→  SQLite (Chat History)
    │
    ▼
Streamlit Frontend
```

---

## How the CRAG Pipeline Works

LegalBuddy's core is a **5-node LangGraph state machine**. Each query flows through the following steps:

### 1. `load_history`
Fetches the user's previous messages from SQLite for the current session and injects them into the graph state. This gives the LLM conversational context for follow-up questions.

### 2. `retrieve`
Queries the local **ChromaDB** vector store using the BAAI/bge-small-en-v1.5 embedding model. Returns the top 3 most semantically similar document chunks.

### 3. `grade_documents`
This is the "corrective" heart of CRAG. For each retrieved document, an LLM-based grader evaluates two dimensions:

| Factor | Description | Scale |
|---|---|---|
| `topical_relevance` | How well the document's main topic matches the query | 1–10 |
| `specific_answer` | How directly the document answers the specific question | 1–10 |

The average score is computed. If **any document scores ≥ 5**, the pipeline proceeds to generation using local data. If **all documents score < 5**, the pipeline routes to a web search instead.

### 4. `web_search` *(conditional)*
If local documents are deemed insufficient, **Tavily Search** is invoked to fetch up-to-date information from the web. Results are wrapped as LangChain `Document` objects and passed forward. This ensures LegalBuddy can answer questions beyond its static knowledge base.

### 5. `generate`
The final answer is produced by **Llama 3.1 8B** (via Groq) using a carefully engineered prompt that:
- Instructs the model to respond conversationally and empathetically
- Grounds the response strictly in the retrieved context
- Explicitly instructs the model to say "I don't know" rather than guess
- Maintains awareness of the full chat history for follow-up continuity

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Orchestration** | LangGraph | CRAG state machine, conditional routing |
| **LLM** | Llama 3.1 8B via Groq | Fast, free-tier inference for generation & grading |
| **Embeddings** | BAAI/bge-small-en-v1.5 (FastEmbed) | Local semantic embeddings, zero inference cost |
| **Vector Store** | ChromaDB | Persistent local vector database |
| **Web Search** | Tavily Search | Fallback retrieval for out-of-scope queries |
| **Backend API** | FastAPI + Uvicorn | REST API serving the RAG pipeline |
| **Frontend** | Streamlit | Conversational chat UI |
| **Chat Memory** | SQLite | Lightweight, persistent per-user/session history |
| **PDF Parsing** | PyPDFLoader | Legal document ingestion |
| **Containerization** | Docker + Docker Compose | Reproducible multi-service deployment |

---

## Project Structure

```
LegalBuddy/
│
├── app/
│   ├── main.py              # FastAPI app — /chat endpoint, startup hooks
│   └── streamlit_app.py     # Streamlit chat UI
│
├── src/
│   ├── rag_pipeline.py      # Core CRAG pipeline (LangGraph state machine)
│   ├── embedding.py         # Embedding model loader (BAAI/bge-small-en-v1.5)
│   ├── vector_store.py      # ChromaDB initialization and document ingestion
│   ├── data_loader.py       # PDF and JSONL document loaders + chunking
│   ├── llm.py               # Groq LLM initialization (Llama 3.1 8B)
│   ├── chat_history.py      # SQLite chat history — read/write helpers
│   └── __init__.py
│
├── data/
│   ├── raw/                 # Source documents (PDFs, JSONL Q&A pairs)
│   └── processed/           # SQLite database (auto-generated)
│
├── db_storage/
│   └── chroma_db/           # Persisted ChromaDB vector store (auto-generated)
│
├── models/                  # Cached embedding models (auto-generated)
│
├── Dockerfile               # Single image for both backend and frontend
├── docker-compose.yml       # Multi-service orchestration
├── render.yaml              # Render.com deployment config
├── requirements.txt         # Python dependencies
└── .env                     # API keys (not committed — see below)
```

---

## Setup & Installation

### Prerequisites

- Python 3.12+
- `poppler-utils` (required by PyPDFLoader for PDF parsing)
- A [Groq API key](https://console.groq.com/) (free tier available)
- A [Tavily API key](https://tavily.com/) (free tier available)

### 1. Clone the repository

```bash
git clone https://github.com/surya-sgit/LegalBuddy.git
cd LegalBuddy
```

### 2. Install system dependencies

```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y poppler-utils

# macOS
brew install poppler
```

### 3. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### 6. Add your legal documents

Place your source files in the `data/raw/` directory:
- `legal_docs.pdf` — Legal statutes or documents to embed
- `train.jsonl` — Legal Q&A pairs (each line: `{"id": ..., "text": [...], "labels": [...]}`)

### 7. Initialize the vector store

```bash
python -m src.vector_store
```

This will embed all documents and populate ChromaDB. Depending on the size of your dataset, this may take a few minutes. It only needs to be run once — ChromaDB persists to disk.

---

## Running the Application

### Run backend and frontend separately

```bash
# Terminal 1 — Start the FastAPI backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Start the Streamlit frontend
streamlit run app/streamlit_app.py
```

- Backend API: `http://localhost:8000`
- Streamlit UI: `http://localhost:8501`

---

## API Reference

### `POST /chat`

Submit a legal query and receive a grounded AI response.

**Request body:**
```json
{
  "query": "What are the bail procedures under the CrPC?",
  "user_id": "user_123",
  "session_id": "session_abc"
}
```

**Response:**
```json
{
  "response": "Under the Code of Criminal Procedure...",
  "user_id": "user_123",
  "session_id": "session_abc"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `query` | `string` | required | The user's legal question |
| `user_id` | `string` | `"default_user"` | Unique user identifier for chat history |
| `session_id` | `string` | `"default_session"` | Session identifier for conversation continuity |

### `GET /`

Health check endpoint.

```json
{ "message": "LegalBuddy API is running. Post queries to /chat" }
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | API key for Groq (LLM inference) |
| `TAVILY_API_KEY` | ✅ Yes | API key for Tavily (web search fallback) |

---

## Docker Deployment

LegalBuddy is fully containerized. Docker Compose spins up both the FastAPI backend and the Streamlit frontend from a single shared image.

```bash
docker-compose up --build
```

| Service | Port | Description |
|---|---|---|
| `backend` | `8000` | FastAPI REST API |
| `frontend` | `8501` | Streamlit chat interface |

Volumes are mounted for `data/` and `db_storage/` so your vector store and chat history persist across container restarts.

---

## Design Decisions

**Why CRAG over standard RAG?**
Standard RAG blindly passes retrieved documents to the LLM regardless of relevance. In a legal context, irrelevant context is worse than no context — it can cause the model to generate confidently wrong answers. The CRAG grading step acts as a quality gate, only using local documents when they actually match the query.

**Why BAAI/bge-small-en-v1.5?**
It offers strong semantic retrieval performance in a small footprint, runs locally with no API cost, and performs well on domain-specific text like legal documents. For a production system, upgrading to a larger model like `bge-large` or a fine-tuned legal embedding model would be the natural next step.

**Why Groq for inference?**
Groq's LPU hardware delivers extremely low-latency inference on open-source models. For a conversational app where response speed directly affects user experience, this was a deliberate choice over higher-latency alternatives.

**Why SQLite for chat history?**
For the current scope and deployment target, SQLite is lightweight, zero-dependency, and sufficient. A production deployment serving multiple concurrent users would benefit from migrating to PostgreSQL.

**Why chunk size 1,000 with 100-token overlap?**
Smaller chunks improve retrieval precision but reduce the context available during generation. Legal documents are dense and often require surrounding context to be interpretable — 1,000 tokens with 100-token overlap was chosen as a practical balance between precision and coherence.

---

*Built by [Surya Prakash Baid](https://github.com/surya-sgit)*
