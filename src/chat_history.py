import sqlite3
import json
import os
from datetime import datetime

# Define the database path
# This points to our new 'data/processed/' folder
DB_PATH = "data/processed/legal_chat.db"

def initialize_database():
    """
    Creates the chat_history table if it doesn't exist.
    """
    # Ensure the 'data/processed' directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        message TEXT NOT NULL,
        sender TEXT NOT NULL CHECK(sender IN ('user', 'bot'))
    );
    """)
    conn.commit()
    conn.close()

def get_user_chat_history(user_id, session_id):
    """
    Retrieves the chat history for a specific user and session.
    (This is your function from cell 13)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message, sender FROM chat_history WHERE user_id = ? AND session_id = ? ORDER BY timestamp ASC",
        (user_id, session_id)
    )
    history = cursor.fetchall()
    conn.close()
    
    # Format for RAG context
    formatted_history = []
    for message, sender in history:
        if sender == 'user':
            formatted_history.append(f"User: {message}")
        else:
            formatted_history.append(f"Bot: {message}")
    return "\n".join(formatted_history)

def save_chat_message(user_id, session_id, message, sender):
    """
    Saves a new chat message to the database.
    (This logic was part of your FastAPI app in cell 18)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_history (user_id, session_id, timestamp, message, sender)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, session_id, datetime.now(), message, sender)
    )
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # This block allows you to test this file directly
    # Run: python src/chat_history.py
    print("Testing chat history database...")
    initialize_database()
    save_chat_message('test_user', 'test_session', 'Hello', 'user')
    save_chat_message('test_user', 'test_session', 'Hi there!', 'bot')
    history = get_user_chat_history('test_user', 'test_session')
    print("Retrieved History:")
    print(history)
    print("chat_history.py is working correctly.")