DataSense AI 🤖
An Interactive Chatbot for Instant CSV & Excel Analysis.

🚀 Live Demo
![DataSense AI Demo](demo.gif)

The Business Problem
Many businesses have valuable data trapped in spreadsheets. To get answers, teams often need to write complex formulas or wait for a data analyst to write code. This process is slow, technical, and creates a roadblock to making smart, fast decisions.

The Solution & Key Features ✨
DataSense AI is a web application built with Streamlit that unlocks your data by providing a seamless, conversational interface for analysis.

💬 Natural Language Q&A: Ask complex questions about your data in plain English ("Which 5 companies had the highest growth?") and receive instant, accurate answers.

📊 Automated Chart & Dashboard Generation: Go beyond numbers. Ask for a specific chart ("create a bar chart of sales by region") or a full dashboard, and the AI will generate beautiful, interactive visualizations using Plotly.

🤖 Instant Data Health Report: The moment you upload a file, the AI performs an initial analysis, checking for missing values and duplicates, and gives you a summary of your dataset's health.

💾 Session Management: Automatically saves each analysis session (the uploaded file + chat history) so you can return to it later, creating a persistent workspace for your projects.

📤 Simple File Upload: Supports both CSV and multi-sheet Excel files (.xls, .xlsx).

Tech Stack ⚙️
Frontend: Streamlit

AI Agent & Orchestration: LangGraph

Language Model (LLM): Google Gemini

Data Manipulation: Pandas

Plotting: Plotly

Getting Started 🏁
Prerequisites

Python 3.9+

A Google Gemini API Key

Installation & Setup

Clone the repository:

Bash

git clone https://github.com/your-username/datasense-ai.git
cd datasense-ai
Create and activate a virtual environment:

Bash

# Create the environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
Install the required dependencies:

Bash

pip install -r requirements.txt
Configure your API Key:
Create a file named .env in the root directory and add your Google Gemini API key:

GOOGLE_API_KEY="YOUR_API_KEY_HERE"
Running the Application

Launch the Streamlit app:

Bash

streamlit run app.py
Open your browser and navigate to http://localhost:8501.

How to Use
Upload: Drag and drop a CSV or Excel file onto the uploader.

Ask: Use the chat input at the bottom to ask questions, request charts, or generate a dashboard.

Explore: Interact with the charts, view the data, and use the sidebar to manage your analysis sessions.

License
This project is licensed under the MIT License. See the LICENSE file for details.