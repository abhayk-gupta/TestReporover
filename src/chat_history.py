import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv
import bcrypt

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Establishes a connection to NeonDB."""
    if not DB_URL:
        raise ValueError("DATABASE_URL is missing in your .env file.")
    return psycopg2.connect(DB_URL)

def initialize_database():
    """Initializes the secure relational database schema on NeonDB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table 1: Secure Users Table (user_id is the unique username)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR(255) PRIMARY KEY,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Table 2: Relational Chat Sessions Thread
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        session_id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        title VARCHAR(255) DEFAULT 'New Legal Case',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Table 3: Messages Table with Optional Source Archiving
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id SERIAL PRIMARY KEY,
        session_id VARCHAR(255) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
        sender VARCHAR(50) NOT NULL CHECK(sender IN ('user', 'bot')),
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        retrieved_sources TEXT
    );
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("[DB] Production schema successfully initialized/verified on NeonDB.")

# --- AUTHENTICATION UTILITIES ---

def register_user(username, plain_password):
    """Registers a new user with a securely hashed password using native bcrypt."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False, "Username already taken."
        
    # Native bcrypt hashing: Convert string to bytes, salt it, and hash it
    password_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password_bytes = bcrypt.hashpw(password_bytes, salt)
    
    # Convert bytes back to a string to store cleanly in PostgreSQL VARCHAR
    hashed_password_str = hashed_password_bytes.decode('utf-8')
    
    try:
        cursor.execute(
            "INSERT INTO users (user_id, password_hash) VALUES (%s, %s)",
            (username, hashed_password_str)
        )
        conn.commit()
        success, msg = True, "Registration successful."
    except Exception as e:
        success, msg = False, f"Database error: {e}"
    finally:
        cursor.close()
        conn.close()
    return success, msg

def authenticate_user(username, plain_password):
    """Verifies user credentials securely against stored hash using native bcrypt."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not result:
        return False, "Invalid username or password."
        
    stored_hash_str = result[0]
    
    # Convert strings back to bytes for bcrypt comparison
    password_bytes = plain_password.encode('utf-8')
    stored_hash_bytes = stored_hash_str.encode('utf-8')
    
    # Verify the password match
    if bcrypt.checkpw(password_bytes, stored_hash_bytes):
        return True, "Login successful."
    return False, "Invalid username or password."

# --- SESSION & CHAT MANAGEMENT ---

def create_chat_session(session_id, user_id, title="New Legal Case"):
    """Ensures a relational chat session exists for data isolation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_sessions (session_id, user_id, title)
        VALUES (%s, %s, %s)
        ON CONFLICT (session_id) DO NOTHING
        """,
        (session_id, user_id, title)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_user_chat_history(user_id, session_id, limit=10):
    """
    Retrieves history for isolation validation.
    Applies a strict sliding window limit to optimize token usage.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Validate session ownership to prevent cross-user data bleed vulnerabilities
    cursor.execute(
        "SELECT user_id FROM chat_sessions WHERE session_id = %s", (session_id,)
    )
    session_owner = cursor.fetchone()
    if not session_owner or session_owner[0] != user_id:
        cursor.close()
        conn.close()
        return "System Warning: Unauthorized history access denied."

    # Fetch with a strict context threshold window
    cursor.execute(
        """
        SELECT message, sender FROM chat_messages 
        WHERE session_id = %s 
        ORDER BY timestamp DESC LIMIT %s
        """,
        (session_id, limit)
    )
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Reverse to restore cronological flow order for context parsing
    history.reverse()
    
    formatted_history = []
    for message, sender in history:
        if sender == 'user':
            formatted_history.append(f"User: {message}")
        else:
            formatted_history.append(f"Bot: {message}")
    return "\n".join(formatted_history)

def save_chat_message(user_id, session_id, message, sender, sources=None):
    """Saves conversation entries securely under relational foreign keys."""
    # Defensively ensure the session mapping layer exists before message insertion
    create_chat_session(session_id, user_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_messages (session_id, sender, message, retrieved_sources)
        VALUES (%s, %s, %s, %s)
        """,
        (session_id, sender, message, sources)
    )
    conn.commit()
    cursor.close()
    conn.close()