import streamlit as st
import pandas as pd
import base64
import time
import os 
from utils import load_sessions_list, get_image_download_link, get_chat_download_link

def display_chat_messages(messages, agent):
    """Displays chat messages and handles UI interactions for charts and follow-up questions."""
    for i, message in enumerate(messages):
        with st.chat_message(message["role"]):
            content = message["content"]
            
            if isinstance(content, str):
                st.markdown(content)
                continue

            if "response_text" in content:
                st.markdown(content["response_text"])

            if "plotly_fig" in content and content["plotly_fig"]:
                st.plotly_chart(content["plotly_fig"], use_container_width=True)

            if "plotly_dashboard" in content and content["plotly_dashboard"]:
                dashboard_figs = content["plotly_dashboard"]
                if dashboard_figs and isinstance(dashboard_figs, list):
                    cols = st.columns(2)
                    for j, fig in enumerate(dashboard_figs):
                        if fig: cols[j % 2].plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("The agent returned an empty or invalid dashboard.")

            if "dataframe" in content and isinstance(content.get("dataframe"), pd.DataFrame) and not content["dataframe"].empty:
                st.dataframe(content["dataframe"])

            if "follow_up_questions" in content and content["follow_up_questions"]:
                st.markdown("**Suggested Follow-ups:**")
                cols = st.columns(min(len(content["follow_up_questions"]), 3))
                for k, question in enumerate(content["follow_up_questions"]):
                    if cols[k].button(question, key=f"follow_up_{i}_{k}_{question}"):
                        st.session_state.messages.append({"role": "user", "content": question})
                        with st.spinner("Thinking..."):
                            response = agent.invoke_agent(question)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                        st.rerun()


def set_clear_session_flag():
    """Callback to safely set the session clear flag."""
    st.session_state.clear_session_request = True

def set_session_to_load(session_file):
    """Callback to safely set the session load flag."""
    st.session_state.session_to_load = session_file


def setup_sidebar():
    """Sets up the sidebar with session management and export buttons."""
    with st.sidebar:
        st.header("DataSense AI")
        st.markdown("Your intelligent data analysis partner.")

       
        st.button("➕ New Analysis", on_click=set_clear_session_flag)
            
        st.markdown("---")

        saved_sessions = load_sessions_list()
        if saved_sessions:
            st.markdown("**Past Analyses** (Auto-Saved)")
            for session_file in saved_sessions:
                session_name = os.path.splitext(session_file)[0]
                
                st.button(
                    f"Load '{session_name}'", 
                    key=f"load_{session_name}",
                    on_click=set_session_to_load,
                    args=(session_file,)
                )
        
        st.markdown("---")
        
        last_fig_msg = next((msg for msg in reversed(st.session_state.messages) if isinstance(msg["content"], dict) and "plotly_fig" in msg["content"]), None)
        if last_fig_msg:
            st.markdown("**Export Last Chart**")
            st.markdown(get_image_download_link(last_fig_msg["content"]["plotly_fig"], "chart.png"), unsafe_allow_html=True)
        
        if st.session_state.messages:
            st.markdown("**Export Chat**")
            st.markdown(get_chat_download_link(st.session_state.messages, "chat_history.html"), unsafe_allow_html=True)