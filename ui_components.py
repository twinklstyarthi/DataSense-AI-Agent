import streamlit as st
import pandas as pd
import base64
import time
import os
from utils import start_new_chat, switch_chat, get_image_download_link, get_chat_download_link

def display_chat_messages(messages, agent):
    """Displays chat messages and handles UI for follow-up questions."""
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
                    if cols[k].button(question, key=f"follow_up_{i}_{k}_{st.session_state.current_chat_id}"):
                        st.session_state.user_prompt_from_followup = question
                        st.rerun()

def setup_sidebar():
    """Sets up the sidebar with session management and export buttons."""
    with st.sidebar:
        st.header("DataSense AI")
        st.markdown("Your intelligent data analysis partner.")
        
        st.button("➕ New Analysis", on_click=start_new_chat, use_container_width=True)
        
        st.markdown("---")

        
        sorted_chat_ids = list(st.session_state.chat_history.keys())[::-1]

        if sorted_chat_ids:
            st.markdown("**Past Analyses**")
            for chat_id in sorted_chat_ids:
                chat_data = st.session_state.chat_history[chat_id]
                session_name = f"'{chat_data.get('df_name', 'Chat')}'"

                if chat_id == st.session_state.current_chat_id:
                    st.markdown(f'<p class="active-chat-item">{session_name}</p>', unsafe_allow_html=True)
                else:
                    st.button(
                        session_name, 
                        key=f"load_{chat_id}",
                        on_click=switch_chat,
                        args=(chat_id,),
                        use_container_width=True
                    )
        
        st.markdown("---")
        
        active_chat = st.session_state.chat_history[st.session_state.current_chat_id]
        
        last_fig_msg = next((msg for msg in reversed(active_chat.get("messages", [])) if isinstance(msg["content"], dict) and "plotly_fig" in msg["content"]), None)
        if last_fig_msg:
            st.markdown("**Export Last Chart**")
            st.markdown(get_image_download_link(last_fig_msg["content"]["plotly_fig"], "chart.png"), unsafe_allow_html=True)
        
        if active_chat.get("messages", []):
            st.markdown("**Export Chat**")
            st.markdown(get_chat_download_link(active_chat["messages"], "chat_history.html"), unsafe_allow_html=True)