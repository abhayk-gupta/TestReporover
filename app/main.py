from dotenv import load_dotenv
load_dotenv()

import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

# --- Imports from our MLOps structure ---
from src.rag_pipeline import get_rag_response
from src.chat_history import (
    save_chat_message, 
    initialize_database, 
    register_user, 
    authenticate_user
)

app = FastAPI(
    title="LegalBuddy API",
    description="Secure Production API for the LegalBuddy RAG Assistant"
)

@app.on_event("startup")
def on_startup():
    print("Initializing Postgres Tables via NeonDB...")
    initialize_database()

# --- AUTHENTICATION SCHEMAS ---
class AuthRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str

# --- CHAT SCHEMAS ---
class ChatQuery(BaseModel):
    query: str
    user_id: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: str

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
async def chat_endpoint(request: ChatQuery):
    """Main isolation-safe chat endpoint."""
    print(f"Received query from {request.user_id}: {request.query}")
    
    # 1. Fetch response through the CRAG graph state engine
    bot_response = get_rag_response(
        query=request.query,
        user_id=request.user_id,
        session_id=request.session_id
    )
    
    # 2. Relational safe logging to NeonDB
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