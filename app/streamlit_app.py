import streamlit as st
import requests
import uuid
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
        try:
            payload = {
                "query": prompt,
                "user_id": st.session_state.user_id,
                "session_id": st.session_state.session_id
            }
            
            # Use stream=True to process the chunked response from FastAPI without waiting
            response = requests.post(f"{API_URL}/chat", json=payload, stream=True)
            
            if response.status_code == 200:
                # Real-Time Token Generator reading from the network stream
                def token_stream():
                    for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                        if chunk:
                            yield chunk
                
                # st.write_stream prints it dynamically and returns the final concatenated string
                full_bot_response = st.write_stream(token_stream())
                
                # Save the final compiled response to session state
                st.session_state.messages.append({"role": "assistant", "content": full_bot_response})
            else:
                err_msg = f"System Error Exception: API returned status {response.status_code}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
                
        except requests.exceptions.ConnectionError:
            err_msg = "Network Error: Could not connect to the core RAG inference API."
            st.error(err_msg)
            st.session_state.messages.append({"role": "assistant", "content": err_msg})