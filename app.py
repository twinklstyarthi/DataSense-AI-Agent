import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import streamlit.components.v1 as components
import subprocess
import sys
import atexit
import tempfile
import os
import platform
import time
import socket
from datetime import datetime

from utils import initialize_session_state, load_css, auto_save_session, load_selected_session
from data_handler import load_data, get_data_quality_report, get_data_summary
from ui_components import display_chat_messages, setup_sidebar
from llm_agent import AIAgent

load_dotenv()
st.set_page_config(
    page_title="DataSense AI",
    page_icon="🤖",
    layout="wide"
)

if st.session_state.get("clear_session_request"):
    st.session_state.clear()
    st.session_state.clear_session_request = False 
    st.rerun()

if st.session_state.get("session_to_load"):
    session_file = st.session_state.session_to_load
    saved_state = load_selected_session(session_file)
    st.session_state.clear()
    for key, value in saved_state.items():
        st.session_state[key] = value
    
    initialize_session_state() 
    st.session_state.session_to_load = None 
    st.rerun()


initialize_session_state()
load_css("styles.css")
setup_sidebar()


def initialize_agent(df):
    """Initializes and returns the AI agent."""
    if df is None: return None
    
    if 'agent' not in st.session_state or st.session_state.agent is None:
        st.session_state.data_summary = get_data_summary(df)
        st.session_state.agent = AIAgent(df=df, data_summary=st.session_state.data_summary)
    return st.session_state.agent

#Process Management
def cleanup_temp_files():
    if 'dtale_temp_csv_file' in st.session_state and st.session_state.dtale_temp_csv_file and os.path.exists(st.session_state.dtale_temp_csv_file):
        os.remove(st.session_state.dtale_temp_csv_file)
    if 'dtale_temp_script_file' in st.session_state and st.session_state.dtale_temp_script_file and os.path.exists(st.session_state.dtale_temp_script_file):
        os.remove(st.session_state.dtale_temp_script_file)

def kill_dtale_process():
    if 'dtale_process' in st.session_state and st.session_state.dtale_process:
        if st.session_state.dtale_process.poll() is None:
            st.session_state.dtale_process.terminate()
        st.session_state.dtale_process = None
    cleanup_temp_files()

atexit.register(kill_dtale_process)

#Main App Logic
st.title("🤖 DataSense AI")
st.markdown("Upload your data and start a conversation. Ask questions, request charts, and build dashboards.")

#File Uploader
if st.session_state.df is None:
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xls", "xlsx"])
    if uploaded_file is not None:
        with st.spinner("Loading and analyzing data..."):
            st.session_state.clear()
            initialize_session_state()
            st.session_state.df = load_data(uploaded_file)
            st.session_state.df_name = uploaded_file.name
            
            if st.session_state.df is not None:
                
                safe_name = "".join(c for c in st.session_state.df_name if c.isalnum() or c in (' ', '.', '_')).rstrip()
                st.session_state.session_id = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{safe_name}"

                report = get_data_quality_report(st.session_state.df)
                st.session_state.messages.append({"role": "assistant", "content": {"response_text": report}})
                
                
                auto_save_session()
                st.rerun()
else:
    st.info(f"**Dataset Loaded:** `{st.session_state.df_name}` ({st.session_state.df.shape[0]} rows, {st.session_state.df.shape[1]} columns)")

#Main Content Tabs
if st.session_state.df is not None:
    agent = initialize_agent(st.session_state.df)
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "🗂️ Data View & Analysis", "📊 Dashboard"])

    with tab1:
        st.header("Conversational Analysis")
        display_chat_messages(st.session_state.messages, agent)
        prompt = st.chat_input("Ask DataSense AI...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("Thinking..."):
                response = agent.invoke_agent(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                auto_save_session()
            st.rerun()

    with tab2:
        st.header("Data Preview")
        st.dataframe(st.session_state.df.head(20))
        st.header("Interactive Analysis")
        DTALE_PORT = 40000
        dtale_url = f"http://127.0.0.1:{DTALE_PORT}"
        if st.session_state.get('dtale_process') is None:
            if st.button("🚀 Launch Interactive Analysis"):
                with st.spinner('Starting D-Tale...'):
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='') as tmp_csv:
                        st.session_state.df.to_csv(tmp_csv.name, index=False)
                        st.session_state.dtale_temp_csv_file = tmp_csv.name
                    script_content = f"""
import dtale, pandas as pd, sys, time
try:
    port = {DTALE_PORT}
    csv_path = r'{st.session_state.dtale_temp_csv_file}'
    df = pd.read_csv(csv_path)
    dtale.show(df, port=port, open_browser=False, host='127.0.0.1', app_root='/', reaper_on=False)
    while True: time.sleep(1)
except KeyboardInterrupt: sys.exit(0)
"""
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode='w') as tmp_script:
                        tmp_script.write(script_content)
                        st.session_state.dtale_temp_script_file = tmp_script.name
                    command = [sys.executable, st.session_state.dtale_temp_script_file]
                    process = subprocess.Popen(command)
                    st.session_state.dtale_process = process
                    is_ready = False
                    start_time = time.time()
                    with st.spinner("Waiting for Interactive Analysis to initialize..."):
                        while time.time() - start_time < 30:
                            try:
                                with socket.create_connection(("127.0.0.1", DTALE_PORT), timeout=1):
                                    is_ready = True
                                    break
                            except (ConnectionRefusedError, socket.timeout):
                                time.sleep(0.5)
                    if is_ready:
                        st.rerun()
                    else:
                        kill_dtale_process()
                        st.error("Failed to start the interactive analysis tool within the time limit.")
        else:
            st.success(f"Interactive analysis is running! [Click here]({dtale_url})")
            if st.button("❌ Terminate Interactive Analysis"):
                kill_dtale_process()
                st.rerun()

    with tab3:
        st.header("Automated Dashboards")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Generate Comprehensive Dashboard", use_container_width=True):
                dashboard_prompt = "Generate a comprehensive dashboard."
                with st.spinner("Building your dashboard..."):
                    response = agent.invoke_agent(dashboard_prompt)
                    st.session_state.dashboard_figures = response.get("plotly_dashboard")
                    if st.session_state.dashboard_figures:
                        
                        auto_save_session()
                    else:
                        st.error(response.get("response_text", "Sorry, the dashboard could not be generated."))
                st.rerun()
        
        numeric_cols = st.session_state.df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = st.session_state.df.select_dtypes(include=['object', 'category']).columns.tolist()

        suggestions = []
        if len(numeric_cols) > 1: suggestions.append(f"Dashboard of {numeric_cols[0]} vs {numeric_cols[1]}")
        if categorical_cols: suggestions.append(f"Dashboard about {categorical_cols[0]}")
        if numeric_cols and categorical_cols: suggestions.append(f"Dashboard of {numeric_cols[0]} by {categorical_cols[0]}")
        
        button_cols = [col2, col3, col4]
        for i, suggestion in enumerate(suggestions[:3]):
            with button_cols[i]:
                if st.button(suggestion, use_container_width=True, key=f"dash_sug_{i}"):
                    with st.spinner(f"Building dashboard for '{suggestion}'..."):
                        response = agent.invoke_agent(suggestion)
                        st.session_state.dashboard_figures = response.get("plotly_dashboard")
                        if st.session_state.dashboard_figures:
                            
                            auto_save_session()
                        else:
                            st.error(response.get("response_text", "Sorry, that dashboard could not be generated."))
                    st.rerun()

        st.markdown("---")
        if st.session_state.get('dashboard_figures'):
            st.subheader("Your Generated Dashboard")
            dashboard_figs = st.session_state.dashboard_figures
            if dashboard_figs and isinstance(dashboard_figs, list):
                cols = st.columns(2)
                for i, fig in enumerate(dashboard_figs):
                    if fig:
                        cols[i % 2].plotly_chart(fig, use_container_width=True)
            else:
                st.warning("The AI did not generate a valid list of figures for the dashboard.")
