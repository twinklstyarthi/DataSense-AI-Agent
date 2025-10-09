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
import time
import socket
from utils import initialize_session_state, load_css, get_active_chat_state, create_chat_for_new_upload
from data_handler import load_data, get_data_quality_report, get_data_summary
from ui_components import display_chat_messages, setup_sidebar
from llm_agent import AIAgent

load_dotenv()
st.set_page_config(
    page_title="DataSense AI",
    page_icon="🤖",
    layout="wide"
)

initialize_session_state()
load_css("styles.css")
setup_sidebar()
active_chat = get_active_chat_state()

def initialize_agent(df):
    """Initializes and returns the AI agent for the active chat."""
    if df is None: return None
    if 'agent' not in active_chat or active_chat['agent'] is None:
        active_chat['data_summary'] = get_data_summary(df)
        active_chat['agent'] = AIAgent(df=df, data_summary=active_chat['data_summary'])
    return active_chat['agent']

#Process Management for D-Tale
def cleanup_temp_files():
    if active_chat and 'dtale_temp_csv_file' in active_chat and active_chat['dtale_temp_csv_file'] and os.path.exists(active_chat['dtale_temp_csv_file']):
        os.remove(active_chat['dtale_temp_csv_file'])
    if active_chat and 'dtale_temp_script_file' in active_chat and active_chat['dtale_temp_script_file'] and os.path.exists(active_chat['dtale_temp_script_file']):
        os.remove(active_chat['dtale_temp_script_file'])

def kill_all_dtale_processes():
    if "chat_history" in st.session_state:
        for chat_id, chat_data in st.session_state.chat_history.items():
            if 'dtale_process' in chat_data and chat_data['dtale_process']:
                if chat_data['dtale_process'].poll() is None:
                    chat_data['dtale_process'].terminate()
                chat_data['dtale_process'] = None

atexit.register(kill_all_dtale_processes)

#Main App Logic
st.title("🤖 DataSense AI")
st.markdown("Upload your data and start a conversation. Ask questions, request charts, and build dashboards.")
user_prompt = None
if "user_prompt_from_followup" in st.session_state and st.session_state.user_prompt_from_followup:
    user_prompt = st.session_state.user_prompt_from_followup
    st.session_state.user_prompt_from_followup = None
else:
    user_prompt = st.chat_input("Ask DataSense AI...")


if active_chat['df'] is None:
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xls", "xlsx"])
    if uploaded_file is not None:
        with st.spinner("Loading and analyzing data..."):
            df = load_data(uploaded_file)
            if df is not None:
                report = get_data_quality_report(df)
                create_chat_for_new_upload(df, uploaded_file.name, report)
else:
    st.info(f"**Dataset Loaded:** `{active_chat['df_name']}` ({active_chat['df'].shape[0]} rows, {active_chat['df'].shape[1]} columns)")

# Main Content Tabs
if active_chat['df'] is not None:
    agent = initialize_agent(active_chat['df'])
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "🗂️ Data View & Analysis", "📊 Dashboard"])

    with tab1:
        st.header("Conversational Analysis")
        display_chat_messages(active_chat['messages'], agent)

    with tab2:
        st.header("Data Preview")
        st.dataframe(active_chat['df'].head(20))
        st.header("Interactive Analysis")
        DTALE_PORT = 40000 
        dtale_url = f"http://127.0.0.1:{DTALE_PORT}"
        
        if active_chat.get('dtale_process') is None:
            if st.button("🚀 Launch Interactive Analysis"):
                with st.spinner('Starting D-Tale...'):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='') as tmp_csv:
                        active_chat['df'].to_csv(tmp_csv.name, index=False)
                        active_chat['dtale_temp_csv_file'] = tmp_csv.name
                    script_content = f"""
import dtale, pandas as pd, sys, time
try:
    port = {DTALE_PORT}
    csv_path = r'{active_chat['dtale_temp_csv_file']}'
    df = pd.read_csv(csv_path)
    dtale.show(df, port=port, open_browser=False, host='127.0.0.1', app_root='/', reaper_on=False)
    while True: time.sleep(1)
except KeyboardInterrupt: sys.exit(0)
"""
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode='w') as tmp_script:
                        tmp_script.write(script_content)
                        active_chat['dtale_temp_script_file'] = tmp_script.name
                    command = [sys.executable, active_chat['dtale_temp_script_file']]
                    process = subprocess.Popen(command)
                    active_chat['dtale_process'] = process
                    
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
                        proc = active_chat.get('dtale_process')
                        if proc and proc.poll() is None: proc.terminate()
                        active_chat['dtale_process'] = None
                        cleanup_temp_files()
                        st.error("Failed to start the interactive analysis tool within the time limit.")
        else:
            st.success(f"Interactive analysis is running! [Click here]({dtale_url})")
            if st.button("❌ Terminate Interactive Analysis"):
                proc = active_chat.get('dtale_process')
                if proc and proc.poll() is None: proc.terminate()
                active_chat['dtale_process'] = None
                cleanup_temp_files()
                st.rerun()

    with tab3:
        st.header("Automated Dashboards")
        
        col1, _, _, _ = st.columns(4)
        with col1:
            if st.button("Generate Comprehensive Dashboard", use_container_width=True):
                with st.spinner("Building your dashboard..."):
                    response = agent.invoke_agent("Generate a comprehensive dashboard.")
                    active_chat['dashboard_figures'] = response.get("plotly_dashboard")
                    if not active_chat['dashboard_figures']:
                        st.error(response.get("response_text", "Sorry, the dashboard could not be generated."))
                
        st.markdown("---")
        if active_chat.get('dashboard_figures'):
            st.subheader("Your Generated Dashboard")
            dashboard_figs = active_chat['dashboard_figures']
            if dashboard_figs and isinstance(dashboard_figs, list):
                cols = st.columns(2)
                for i, fig in enumerate(dashboard_figs):
                    if fig: cols[i % 2].plotly_chart(fig, use_container_width=True)
            else:
                st.warning("The AI did not generate a valid list of figures for the dashboard.")

# Process user input
if user_prompt and agent:
    active_chat['messages'].append({"role": "user", "content": user_prompt})
    with st.spinner("Thinking..."):
        response = agent.invoke_agent(user_prompt)
        active_chat['messages'].append({"role": "assistant", "content": response})
    st.rerun()