import streamlit as st
import requests
import uuid
import time
import os

# --- Resilient Dynamic Routing Fallback ---
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="LegalBuddy",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom scannable sidebar component design elements
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .stButton>button {
        width: 100%; border: 2px solid #4CAF50; background-color: transparent;
        color: #4CAF50; padding: 10px 24px; border-radius: 8px; transition-duration: 0.4s;
    }
    .stButton>button:hover { background-color: #4CAF50; color: white; }
</style>
""", unsafe_allow_html=True)

def stream_data(text: str):
    """Yields words from the text with a small delay for the typing effect."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)

# --- Session State Verification ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- Real Network Identity Authentication Layer ---
if not st.session_state.authenticated:
    st.sidebar.header("Identity Access Verification")
    tab1, tab2 = st.sidebar.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("Login Form"):
            username = st.text_input("Username (Case Sensitive)")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                try:
                    res = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
                    if res.status_code == 200:
                        st.session_state.user_id = username
                        st.session_state.session_id = str(uuid.uuid4())
                        st.session_state.authenticated = True
                        st.session_state.messages = []
                        st.rerun()
                    else:
                        st.error(res.json().get("detail", "Access Denied."))
                except requests.exceptions.ConnectionError:
                    st.error("Authentication Server unreachable. Validate your backend port connection strings.")
                    
    with tab2:
        with st.form("Registration Form"):
            new_user = st.text_input("Desired Username")
            new_pass = st.text_input("Secure Password", type="password")
            if st.form_submit_button("Create Account"):
                try:
                    res = requests.post(f"{API_URL}/register", json={"username": new_user, "password": new_pass})
                    if res.status_code == 200:
                        st.success("Account securely provisioned! Please navigate to the Login tab.")
                    else:
                        st.error(res.json().get("detail", "Registration rejected."))
                except requests.exceptions.ConnectionError:
                    st.error("Authentication Server unreachable.")
    st.stop()

# --- Main Isolated User Workflow Context ---
st.title("⚖️ LegalBuddy AI-Powered Legal Assistant")

with st.sidebar:
    st.write(f"Logged in security profile: **{st.session_state.user_id}**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("New Case"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("Sign Out"):
            st.session_state.clear()
            st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.write(f"Secure Thread Token: `{st.session_state.session_id[:8]}...`")

# Render active working state chat interface strings
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("State your legal question or case incident particulars:"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    with st.chat_message("assistant"):
        with st.spinner("Analyzing verified legal database namespaces..."):
            try:
                payload = {
                    "query": prompt,
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id
                }
                response = requests.post(f"{API_URL}/chat", json=payload)
                if response.status_code == 200:
                    bot_response = response.json()["response"]
                else:
                    bot_response = f"System Error Exception: API returned status {response.status_code}"
            except requests.exceptions.ConnectionError:
                bot_response = "Network Error: Could not connect to the core RAG inference API."
                
        st.write_stream(stream_data(bot_response))
        st.session_state.messages.append({"role": "assistant", "content": bot_response})