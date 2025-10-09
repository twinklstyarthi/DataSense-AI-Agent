import streamlit as st
import base64
import pandas as pd
from datetime import datetime
import uuid
import os

def initialize_session_state():
    """
    Initializes a session-isolated, multi-chat state. Each user session
    gets its own st.session_state, and we store all chat histories within it.
    """
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}

    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None

    if not st.session_state.current_chat_id or st.session_state.current_chat_id not in st.session_state.chat_history:
        first_chat_id = f"chat_{uuid.uuid4()}"
        st.session_state.current_chat_id = first_chat_id
        st.session_state.chat_history[first_chat_id] = {
            "df": None, "df_name": "New Analysis", "messages": [], "agent": None,
            "data_summary": None, "dashboard_figures": None, "dtale_process": None,
            "dtale_temp_csv_file": None, "dtale_temp_script_file": None,
        }

def get_active_chat_state():
    """Returns the state dictionary of the currently active chat."""
    chat_id = st.session_state.current_chat_id
    return st.session_state.chat_history.get(chat_id)

def start_new_chat():
    """Creates a new, blank chat session and switches to it."""
    new_chat_id = f"chat_{uuid.uuid4()}"
    st.session_state.chat_history[new_chat_id] = {
        "df": None, "df_name": "New Analysis", "messages": [], "agent": None,
        "data_summary": None, "dashboard_figures": None, "dtale_process": None,
        "dtale_temp_csv_file": None, "dtale_temp_script_file": None,
    }
    st.session_state.current_chat_id = new_chat_id
    
def switch_chat(chat_id: str):
    """Switches the active chat to the given chat_id."""
    if chat_id in st.session_state.chat_history:
        st.session_state.current_chat_id = chat_id
    
def create_chat_for_new_upload(df, df_name, report):
    """
    Creates a new chat for an uploaded file, or repurposes the current
    chat if it's an empty "New Analysis" session.
    """
    active_chat = get_active_chat_state()

    if active_chat and active_chat['df'] is None:
        chat_id_to_update = st.session_state.current_chat_id
        st.session_state.chat_history[chat_id_to_update].update({
            "df": df,
            "df_name": df_name,
            "messages": [{"role": "assistant", "content": {"response_text": report}}],
            "agent": None,
        })
    else:
        new_chat_id = f"chat_{uuid.uuid4()}"
        st.session_state.chat_history[new_chat_id] = {
            "df": df, "df_name": df_name, "messages": [{"role": "assistant", "content": {"response_text": report}}],
            "agent": None, "data_summary": None, "dashboard_figures": None,
            "dtale_process": None, "dtale_temp_csv_file": None, "dtale_temp_script_file": None,
        }
        st.session_state.current_chat_id = new_chat_id
    
    st.rerun() 


def load_css(file_name):
    """Loads a CSS file."""
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def get_image_download_link(fig, filename):
    """Generates a download link for a Plotly figure."""
    try:
        img_bytes = fig.to_image(format="png", scale=2)
        b64 = base64.b64encode(img_bytes).decode()
        return f'<a href="data:image/png;base64,{b64}" download="{filename}" class="st-emotion-cache-1oe5cao e1nzilvr5"><button class="st-emotion-cache-7ym5gk e1nzilvr4">Export as PNG</button></a>'
    except Exception:
        return "<p style='color:red;'>Could not export chart.</p>"

def get_chat_download_link(messages, filename):
    """Generates a download link for the chat history."""
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