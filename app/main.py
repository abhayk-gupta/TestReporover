import hashlib
import json
import os

import requests
import uvicorn
import hashlib
import asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# --- Imports from our MLOps structure ---
# We now import the compiled LangGraph engine directly
from src.rag_pipeline import app as graph_engine, lc_embedder
from src.chat_history import (
    save_chat_message, 
    initialize_database, 
    register_user, 
    authenticate_user
)

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

# --- BACKGROUND WORKER (Now Synchronous for Threading) ---
def sync_populate_cache(optimized_search_string: str, document_chunks: list):
    """Synchronously logs vector definitions to Upstash (Runs in a background thread)."""
    upstash_url = os.getenv("UPSTASH_VECTOR_REST_URL")
    upstash_token = os.getenv("UPSTASH_VECTOR_REST_TOKEN")

    if not upstash_url or not upstash_token or not document_chunks:
        print("   [Cache Worker Error]: Missing Upstash Credentials or Documents.")
        return

    try:
        base_url = upstash_url.rstrip('/')
        query_vector = lc_embedder.embed_query(optimized_search_string)
        
        packaged_payload = json.dumps([
            {"page_content": item.page_content, "metadata": item.metadata}
            for item in document_chunks
        ])
        
        stable_id = f"cache_{hashlib.md5(optimized_search_string.encode()).hexdigest()}"
        headers = {"Authorization": f"Bearer {upstash_token}", "Content-Type": "application/json"}
        payload = {
            "id": stable_id,
            "vector": query_vector,
            "metadata": {"documents": packaged_payload}
        }

        res = requests.post(f"{base_url}/upsert", headers=headers, json=payload)
        
        if res.status_code == 200:
            print("   [Async Cache Worker]: ✨ Successfully cached text chunks onto Upstash Vector index.")
        else:
            print(f"   [Async Cache Worker ERROR]: Upstash rejected the upload. Status: {res.status_code} Details: {res.text}")
            
    except Exception as e:
        print(f"Background cache ingestion encountered an error: {e}")


# --- ENDPOINTS ---
@app.post("/register", response_model=AuthResponse)
def register_endpoint(payload: AuthRequest):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Missing username or password.")
    success, msg = register_user(payload.username, payload.password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return AuthResponse(success=True, message=msg)

@app.post("/login", response_model=AuthResponse)
def login_endpoint(payload: AuthRequest):
    success, msg = authenticate_user(payload.username, payload.password)
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)
    return AuthResponse(success=True, message=msg)


# --- STREAMING CHAT ENDPOINT ---
@app.post("/chat")
async def chat_endpoint(request: ChatQuery):
    print(f"Received streaming query from '{request.user_id}': {request.query}")
    
    async def response_generator():
        inputs = {"question": request.query, "user_id": request.user_id, "session_id": request.session_id}
        final_generation = ""
        final_state = {}
        
        try:
            # 1. Listen to the Graph Events dynamically
            async for event in graph_engine.astream_events(inputs, version="v2"):
                kind = event["event"]
                tags = event.get("tags", [])
                name = event["name"]
                
                # Catch Real-Time LLM Tokens from tagged nodes
                if kind == "on_chat_model_stream" and "final_node" in tags:
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        final_generation += chunk.content
                        yield chunk.content
                        
                # Catch Instant Hardcoded Routes (Greetings/Blocks)
                elif kind == "on_chain_end" and name in ["handle_greeting", "handle_out_of_scope"]:
                    output = event["data"].get("output", {})
                    if isinstance(output, dict) and "generation" in output:
                        final_generation += output["generation"]
                        yield output["generation"]
                        
                # Accumulate final state context silently
                elif kind == "on_chain_end":
                    output = event["data"].get("output", {})
                    if isinstance(output, dict):
                        if "intent" in output: final_state["intent"] = output["intent"]
                        if "cache_hit" in output: final_state["cache_hit"] = output["cache_hit"]
                        if "documents" in output: final_state["documents"] = output["documents"]
                        if "optimized_query" in output: final_state["optimized_query"] = output["optimized_query"]
                        
        finally:
            # POST-STREAM OPERATIONS
            # These execute instantly after the stream finishes delivering to the user.
            
            # 1. Securely log completed history to NeonDB (Using async thread wrappers to prevent blocking)
            if final_generation:
                asyncio.create_task(asyncio.to_thread(save_chat_message, request.user_id, request.session_id, request.query, "user"))
                asyncio.create_task(asyncio.to_thread(save_chat_message, request.user_id, request.session_id, final_generation, "bot"))
            
            # 2. Safely fire Upstash caching logic into a background thread
            if final_state.get("intent") == "legal_search" and not final_state.get("cache_hit") and final_state.get("documents"):
                asyncio.create_task(
                    asyncio.to_thread(
                        sync_populate_cache, 
                        final_state["optimized_query"], 
                        final_state["documents"]
                    )
                )

    # Return raw streaming bytes to match the Next.js TextDecoder setup
    return StreamingResponse(response_generator(), media_type="text/plain")

@app.get("/")
def root():
    return {"message": "LegalBuddy Production API is running."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
