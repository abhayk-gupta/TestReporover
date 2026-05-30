import hashlib
import json
import os

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from src.chat_history import (
    authenticate_user,
    initialize_database,
    register_user,
    save_chat_message,
)

# --- Imports from our MLOps structure ---
from src.rag_pipeline import get_rag_response, lc_embedder

app = FastAPI(
    title="LegalBuddy API",
    description="Production Secure API Framework for LegalBuddy CRAG"
)

# ---- CONFIGURE CORS MIDDLEWARE HERE ----
# This intercepts browser preflight OPTIONS requests and prevents 405 errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL where your Next.js app runs
    allow_credentials=True,
    allow_methods=["*"],                      # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],                      # Allows Content-Type, Authorization, etc.
)

@app.on_event("startup")
def on_startup():
    print("Validating Relational Postgres Schemas on NeonDB...")
    initialize_database()

# Upstash Environment REST Credentials
UPSTASH_URL = os.getenv("UPSTASH_VECTOR_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_VECTOR_REST_TOKEN")

# --- DATA MODEL SCHEMAS ---
class AuthRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str

class ChatQuery(BaseModel):
    query: str
    user_id: str = "default_user"
    session_id: str = "default_session"

class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: str

# --- BACKGROUND ASYNC ASSET WORKERS ---
def async_populate_cache(optimized_search_string: str, document_chunks: list):
    """Asynchronously logs vector definitions to Upstash on local cache misses."""
    if not UPSTASH_URL or not UPSTASH_TOKEN or not document_chunks:
        print("   [Cache Worker Error]: Missing Upstash Credentials or Documents.")
        return

    try:
        # Strip trailing slashes from URL just in case it was copied weirdly from the .env
        base_url = UPSTASH_URL.rstrip('/')

        # Generate the vector coordinate
        query_vector = lc_embedder.embed_query(optimized_search_string)

        # Serialize the chunks
        packaged_payload = json.dumps([
            {"page_content": item.page_content, "metadata": item.metadata}
            for item in document_chunks
        ])

        # Create a STABLE ID using hashlib (Python's built-in hash() randomizes on server restart)
        stable_id = f"cache_{hashlib.md5(optimized_search_string.encode()).hexdigest()}"

        headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "id": stable_id,
            "vector": query_vector,
            "metadata": {"documents": packaged_payload}
        }

        res = requests.post(f"{base_url}/upsert", headers=headers, json=payload)

        # --- NEW: PROPER ERROR LOGGING ---
        if res.status_code == 200:
            print("   [Async Cache Worker]: ✨ Successfully cached text chunks onto Upstash Vector index.")
        else:
            print("   [Async Cache Worker ERROR]: Upstash rejected the upload.")
            print(f"   Status Code: {res.status_code}")
            print(f"   Details: {res.text}") # <--- This will tell us exactly why it's failing!

    except Exception as e:
        print(f"Background asynchronous cache ingestion encountered an error: {e}")

# --- ENDPOINTS ---

@app.post("/register", response_model=AuthResponse)
def register_endpoint(payload: AuthRequest):
    """Handles secure user enrollment."""
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Missing username or password.")
    success, msg = register_user(payload.username, payload.password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return AuthResponse(success=True, message=msg)

@app.post("/login", response_model=AuthResponse)
def login_endpoint(payload: AuthRequest):
    """Verifies security credentials."""
    success, msg = authenticate_user(payload.username, payload.password)
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)
    return AuthResponse(success=True, message=msg)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatQuery, background_tasks: BackgroundTasks):
    """Data-isolated API endpoint powering conversational routing and caching."""
    print(f"Received query from security profile '{request.user_id}': {request.query}")

    # 1. Dispatch query to compiled agent engine
    result_payload = get_rag_response(
        query=request.query,
        user_id=request.user_id,
        session_id=request.session_id
    )
    bot_response = result_payload["generation"]

    # 2. Log message elements cleanly to database schema rows
    save_chat_message(
        user_id=request.user_id,
        session_id=request.session_id,
        message=request.query,
        sender="user"
    )
    save_chat_message(
        user_id=request.user_id,
        session_id=request.session_id,
        message=bot_response,
        sender="bot"
    )

    # 3. Handle asynchronous cache populating via background worker thread
    if (
        result_payload.get("intent") == "legal_search"
        and not result_payload.get("cache_hit")
        and result_payload.get("documents")
    ):
        background_tasks.add_task(
            async_populate_cache,
            result_payload["optimized_query"],
            result_payload["documents"]
        )

    return ChatResponse(
        response=bot_response,
        user_id=request.user_id,
        session_id=request.session_id
    )

@app.get("/")
def root():
    return {"message": "LegalBuddy Production API is running."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
