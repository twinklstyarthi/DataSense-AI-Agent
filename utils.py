import streamlit as st
import pickle
import os
import base64
import pandas as pd
from datetime import datetime

#Session Management
SESSIONS_DIR = "sessions"
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)


SAVABLE_STATE_KEYS = [
    "df", "df_name", "messages", "data_summary", 
    "dashboard_figures", "session_id"
]

def auto_save_session():
    """Saves the current essential session state to a file named after the session_id."""
    if 'session_id' not in st.session_state or not st.session_state.session_id:
        print("Error: Could not save session. No session_id found.")
        return
        
    try:
        session_copy = {}
        for key in SAVABLE_STATE_KEYS:
            if key in st.session_state:
                session_copy[key] = st.session_state[key]
        
        filename = f"{st.session_state.session_id}.pkl"
        filepath = os.path.join(SESSIONS_DIR, filename)
        with open(filepath, "wb") as f:
            pickle.dump(session_copy, f)
    except Exception as e:
        print(f"Error during auto-save: {e}")

def load_sessions_list():
    """Returns a sorted list of saved session filenames."""
    files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".pkl")]
    return sorted(files, key=lambda f: os.path.getmtime(os.path.join(SESSIONS_DIR, f)), reverse=True)

def load_selected_session(filename):
    """Loads a selected session from a pickle file and returns the state dictionary."""
    filepath = os.path.join(SESSIONS_DIR, filename)
    with open(filepath, "rb") as f:
        saved_state = pickle.load(f)
    return saved_state

#Initial State & CSS 
def initialize_session_state():
    """Initializes the session state with default values if they don't exist."""
    defaults = {
        "df": None, "df_name": "Untitled", "messages": [], "agent": None,
        "data_summary": None, "dashboard_figures": None, "dtale_process": None,
        "dtale_temp_csv_file": None, "dtale_temp_script_file": None,
        "session_to_load": None, 
        "clear_session_request": False,
        "session_id": None  
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def load_css(file_name):
    """Loads a CSS file."""
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

#Export Utilities 
def get_image_download_link(fig, filename):
    try:
        img_bytes = fig.to_image(format="png", scale=2)
        b64 = base64.b64encode(img_bytes).decode()
        return f'<a href="data:image/png;base64,{b64}" download="{filename}" class="st-emotion-cache-1oe5cao e1nzilvr5"><button class="st-emotion-cache-7ym5gk e1nzilvr4">Export as PNG</button></a>'
    except Exception:
        return "<p style='color:red;'>Could not export chart.</p>"

def get_chat_download_link(messages, filename):
    html = "<html><head><title>Chat History</title><style>body {font-family: sans-serif;} .user {color: blue;} .assistant {color: green;}</style></head><body>"
    for msg in messages:
        role = msg['role']
        if isinstance(msg['content'], dict):
            content = msg['content'].get('response_text', str(msg['content']))
        else:
            content = msg['content']
        html += f'<div class="{role}"><b>{role.title()}:</b> {content}</div><hr>'
    html += "</body></html>"
    b64 = base64.b64encode(html.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{filename}" class="st-emotion-cache-1oe5cao e1nzilvr5"><button class="st-emotion-cache-7ym5gk e1nzilvr4">Export as HTML</button></a>'