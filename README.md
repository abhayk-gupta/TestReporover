# LegalBuddy: AI-Powered Legal Assistant

LegalBuddy is an Corrective Retrieval-Augmented Generation (CRAG) system designed to evaluate complex Indian statutory frameworks. The application features a decoupled architecture combining an asynchronous FastAPI streaming backend with a modern Next.js UI workspace.

## System Architecture

The application is split into two independent services:
1. **Backend Service (`app/`, `src/`)**: Built with FastAPI and LangGraph. It runs analytical context-grading nodes, streams generated tokens via HTTP Chunked Transfer Encoding, queries Upstash Vector DB, and logs message events to NeonDB (PostgreSQL).
2. **Frontend Service (`frontend/`)**: Built with Next.js (App Router), TypeScript, and Tailwind CSS. It communicates asynchronously via the browser `ReadableStream` interface to render legal opinions with sub-second initial token latency.

---

## Repository Directory Structure

```text
LegalBuddy/
├── app/                      # FastAPI Server & Request Routers
│   └── main.py               # Core App and Streaming Endpoints
├── src/                      # ML Logic & Specialized RAG Subsystems
│   ├── chat_history.py       # Relational Logging to NeonDB
│   ├── data_loader.py        # PDF Parsing & Chunk Preprocessing
│   ├── embedding.py          # Vector Mapping (HuggingFace)
│   ├── llm.py                # Core Inference Engine Bindings
│   └── rag_pipeline.py       # LangGraph Workflows & Context Routing
├── frontend/                 # Decoupled Web Workspace Client
│   ├── app/                  # Next.js App Router (Layouts & Global Styles)
│   ├── components/           # UI Elements (AuthForm, Sidebar, ChatWindow)
│   ├── Dockerfile.frontend   # Node Environment Build Manifest
│   ├── tailwind.config.ts    # Custom Design Tokens & Layout Spec
│   └── package.json          # Node Dependencies & Package Metadata
├── Dockerfile                # Backend Service Build Manifest
├── docker-compose.yml        # Orchestration Blueprint for Local Multi-Services
└── render.yaml               # Managed Infrastructure Deployment Pipeline

```

---

## Core Technical Features

* **End-to-End Token Streaming**: Bypasses buffered JSON payloads using FastAPI `StreamingResponse` and browser-native `TextDecoder` streams to update components in real time.
* **Multi-Session Workspaces**: Users can create, switch, and isolate separate case historical threads without context crossover.
* **Secure Access Safeguards**: Password masking toggles integrated inside form blocks to maximize user control.
* **Strict Layout Boundaries**: Typography optimized at standard base sizes (`text-base`, `leading-relaxed`) with layout safeguards against duplicate streams.

---

## Technical Stack Configuration

* **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide Icons
* **Backend**: Python 3.10+, FastAPI, LangGraph, Uvicorn
* **Databases**: NeonDB (Relational PostgreSQL Database), Upstash Vector (High-speed Caching Layer)

---

## Local Development Operations

### Environment Variables (.env)

Create a `.env` file in the project root directory containing the following infrastructure parameters:

```env
# Infrastructure API Tokens
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
PINECONE_API_KEY=pinecone_api_key
PINECONE_ENVIRONMENT="us-east-1"
PINECONE_INDEX_NAME="legalbuddy-index"

# NeonDB Relational Configuration
DATABASE_URL=postgres://user:password@endpoint.neon.tech/dbname?sslmode=require

# Upstash Cache Configuration
UPSTASH_VECTOR_REST_URL=[https://endpoint.upstash.io](https://endpoint.upstash.io)
UPSTASH_VECTOR_REST_TOKEN=your_upstash_token

```

### Option A: Execution via Docker Compose (Recommended)

To compile and launch both backend and frontend applications concurrently within isolated networks, run:

```bash
docker-compose up --build

```

* Frontend Application Endpoint: `http://localhost:3000`
* Backend Application API Context: `http://localhost:8000`

### Option B: Local Manual Execution

#### 1. Spin up Backend

```bash
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

```

#### 2. Spin up Frontend

```bash
cd frontend
npm install
npm run dev

```

---

## API Integration Schema

### 1. Account Creation (`/register`)

* **Method**: `POST`
* **Payload Format**: `application/json`
* **Parameters**: `{ "username": "string", "password": "string" }`

### 2. Session Validation (`/login`)

* **Method**: `POST`
* **Payload Format**: `application/json`
* **Parameters**: `{ "username": "string", "password": "string" }`

### 3. Contextual RAG Stream (`/chat`)

* **Method**: `POST`
* **Payload Format**: `application/json`
* **Parameters**: `{ "query": "string", "user_id": "string", "session_id": "string" }`
* **Response Protocol**: `text/plain` using Chunked Transfer Encoding for real-time text delivery.

## Contributors

This repository is developed and contributed by **Surya Prakash Baid** and **Abhay Kumar Gupta**.
