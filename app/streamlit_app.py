import streamlit as st
import requests
import uuid
import time

# --- API Endpoint ---
API_URL = "http://127.0.0.1:8000/chat"

# --- Page Configuration (Makes it look professional) ---
st.set_page_config(
    page_title="LegalBuddy",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS (Fixes "Ugly Buttons") ---
st.markdown("""
<style>
    /* Main app padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Sidebar button styling */
    .stButton>button {
        width: 100%;
        border: 2px solid #4CAF50; /* Green border */
        background-color: transparent;
        color: #4CAF50; /* Green text */
        padding: 10px 24px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 8px;
        transition-duration: 0.4s;
    }
    .stButton>button:hover {
        background-color: #4CAF50; /* Green background on hover */
        color: white; /* White text on hover */
    }
    /* Custom styles for the two columns in sidebar */
    div[data-testid="stHorizontalBlock"] {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- Generator for Typing Effect ---
def stream_data(text: str):
    """Yields words from the text with a small delay for the typing effect."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)

# --- Session State Management ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- Authentication UI ---
if not st.session_state.authenticated:
    st.sidebar.header("Authentication")
    tab1, tab2 = st.sidebar.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                st.session_state.user_id = username
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.authenticated = True
                st.session_state.messages = []
                st.rerun()
                
    with tab2:
        with st.form("Register"):
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            if st.form_submit_button("Register"):
                st.session_state.user_id = new_user
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.authenticated = True
                st.session_state.messages = []
                st.success("Registration successful! You are logged in.")
                st.rerun()
    st.stop()

# --- Main App Interface ---

st.title("🧾 LegalBuddy – AI-Powered Legal Assistant")

# --- Sidebar (Logged-in controls) ---
with st.sidebar:
    st.write(f"Logged in as: **{st.session_state.user_id}**")
    
    # --- FIX: Clean Button Layout ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button("New Chat"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"Session ID: `{st.session_state.session_id[:8]}...`")

# --- Chat Display Logic (Fixes Duplicate Query) ---

# 1. Display all messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. Get new user input
if prompt := st.chat_input("What is your legal question?"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display the user message *immediately*
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process and display the bot's response
    with st.chat_message("assistant"):
        with st.spinner("Consulting legal documents..."):
            try:
                payload = {
                    "query": prompt,
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id
                }
                response = requests.post(API_URL, json=payload)
                
                if response.status_code == 200:
                    bot_response = response.json()["response"]
                else:
                    bot_response = f"Error: API returned status {response.status_code}\n{response.text}"
            
            except requests.exceptions.ConnectionError:
                bot_response = "Error: Could not connect to the API. Is the FastAPI server running?"
        
        # Use the typing effect
        st.write_stream(stream_data(bot_response))
        
        # Add the *full* bot response to history
        st.session_state.messages.append({"role": "assistant", "content": bot_response})