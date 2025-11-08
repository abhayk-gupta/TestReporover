from dotenv import load_dotenv
load_dotenv()
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# --- Imports from our MLOps structure ---
from src.rag_pipeline import get_rag_response
from src.chat_history import save_chat_message, initialize_database

# --- FastAPI App ---
app = FastAPI(
    title="LegalBuddy API",
    description="API for the LegalBuddy RAG-powered legal assistant"
)

# 1. Initialize the chat history database on startup
@app.on_event("startup")
def on_startup():
    print("Initializing chat history database...")
    initialize_database()
    print("Database initialized.")

# 2. Define the request model (what the user sends)
class ChatQuery(BaseModel):
    query: str
    user_id: str = "default_user"
    session_id: str = "default_session"

# 3. Define the response model (what the server sends)
class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: str

# 4. Define the main /chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatQuery):
    """
    Main chat endpoint to get a RAG response.
    """
    # 1. Get the RAG response from our pipeline
    print(f"Received query: {request.query}")
    bot_response = get_rag_response(
        query=request.query,
        user_id=request.user_id,
        session_id=request.session_id
    )
    print(f"Generated response: {bot_response}")

    # 2. Save the user message to history
    save_chat_message(
        user_id=request.user_id,
        session_id=request.session_id,
        message=request.query,
        sender="user"
    )
    
    # 3. Save the bot response to history
    save_chat_message(
        user_id=request.user_id,
        session_id=request.session_id,
        message=bot_response,
        sender="bot"
    )

    # 4. Return the response
    return ChatResponse(
        response=bot_response,
        user_id=request.user_id,
        session_id=request.session_id
    )

# 5. Add a simple root endpoint
@app.get("/")
def root():
    return {"message": "LegalBuddy API is running. Post queries to /chat"}

# 6. Run the app with Uvicorn (if this file is run directly)
if __name__ == "__main__":
    # This allows you to run: python app/main.py
    print("Starting FastAPI server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)