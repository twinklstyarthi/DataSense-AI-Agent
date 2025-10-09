import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
import re
import json

pio.templates.default = "plotly_white"

class BarChartParams(BaseModel):
    x_col: str = Field(description="The column for the x-axis.")
    y_col: str = Field(description="The column for the y-axis.")
    title: str = Field(description="The chart title.")

class HistogramParams(BaseModel):
    col: str = Field(description="The column for the histogram.")
    title: str = Field(description="The chart title.")

class FollowUp(BaseModel):
    questions: List[str] = Field(description="List of 2-3 follow-up questions.", max_items=3)

class AgentState(TypedDict):
    user_prompt: str
    data_summary: str
    dataframe: Any
    intent: str
    tool_params: Dict[str, Any]
    code_string: str
    execution_result: Any
    final_response: Dict[str, Any]
    error: str
    retries: int

def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> dict:
    try:
        fig = px.bar(df, x=x_col, y=y_col, title=title)
        return {"plotly_fig": fig}
    except Exception as e:
        return {"error": str(e)}

def create_histogram(df: pd.DataFrame, col: str, title: str) -> dict:
    try:
        fig = px.histogram(df, x=col, title=title)
        return {"plotly_fig": fig}
    except Exception as e:
        return {"error": str(e)}

class AIAgent:
    MAX_RETRIES = 2

    def __init__(self, df: pd.DataFrame, data_summary: str):
        self.df = df
        self.data_summary = data_summary
        self.llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash", temperature=0, google_api_key=os.getenv("GOOGLE_API_KEY"))
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("intent_router", self.intent_router_node)
        workflow.add_node("parameter_extractor", self.parameter_extractor_node)
        workflow.add_node("tool_executor", self.tool_executor_node)
        workflow.add_node("code_generator", self.code_generator_node)
        workflow.add_node("code_executor", self.code_executor_node)
        workflow.add_node("response_generator", self.response_generator_node)
        workflow.add_node("replan_node", self.replan_node)

        workflow.set_entry_point("intent_router")
        workflow.add_conditional_edges("intent_router", self.decide_next_node, {"tool_user": "parameter_extractor", "code_generator": "code_generator"})
        workflow.add_conditional_edges("parameter_extractor", self.decide_after_params, {"execute_tool": "tool_executor", "fallback_to_code": "code_generator"})
        workflow.add_edge("tool_executor", "response_generator")
        workflow.add_edge("code_generator", "code_executor")
        workflow.add_conditional_edges("code_executor", self.decide_after_code_execution, {"re-plan": "replan_node", "generate_response": "response_generator", "end_with_error": END})
        workflow.add_edge("replan_node", "code_generator")
        workflow.add_edge("response_generator", END)
        return workflow.compile()

    def invoke_agent(self, user_prompt: str) -> Dict[str, Any]:
        inputs = {"user_prompt": user_prompt, "data_summary": self.data_summary, "dataframe": self.df, "retries": 0, "error": ""}
        try:
            final_state = self.graph.invoke(inputs, {"recursion_limit": 15})
            if final_state.get("error") and not final_state.get("final_response"):
                return {"response_text": f"I'm sorry, I was unable to complete your request. The final error was:\n\n`{final_state['error']}`"}
            return final_state.get("final_response", {"response_text": "Sorry, I couldn't process your request."})
        except Exception as e:
            return {"response_text": f"An unexpected system error occurred: {str(e)}"}

    def intent_router_node(self, state: AgentState) -> Dict[str, str]:
        prompt = f"""You are an expert intent router. Classify the user's intent into ONE of the following: 'bar_chart', 'histogram', 'dashboard', or 'code_generator'.
Data Summary: {state['data_summary']}
User Prompt: "{state['user_prompt']}"
Respond with a single, valid JSON object with one key, "intent". Example: {{"intent": "bar_chart"}}"""
        try:
            structured_llm = self.llm.with_structured_output({"intent": str})
            response = structured_llm.invoke(prompt)
            return {"intent": response['intent']}
        except Exception:
            return {"intent": "code_generator"}

    def decide_next_node(self, state: AgentState) -> str:
        return "tool_user" if state["intent"] in ["bar_chart", "histogram"] else "code_generator"

    def decide_after_params(self, state: AgentState) -> str:
        return "fallback_to_code" if state.get("error") else "execute_tool"

    def parameter_extractor_node(self, state: AgentState) -> Dict[str, Any]:
        schema = {"bar_chart": BarChartParams, "histogram": HistogramParams}.get(state["intent"])
        if not schema: return {"error": "Invalid intent for parameter extraction."}
        tool_llm = self.llm.bind_tools(tools=[schema])
        prompt = f"""Extract parameters for '{state['intent']}'. Data Summary: {state['data_summary']}. User Prompt: "{state['user_prompt']}". Ensure column names are exact."""
        try:
            response = tool_llm.invoke(prompt)
            if not response.tool_calls: raise ValueError("Missing necessary information (e.g., column names).")
            return {"tool_params": response.tool_calls[0]['args'], "error": ""}
        except Exception as e:
            return {"error": f"Parameter Extraction Failed: {e}"}

    def tool_executor_node(self, state: AgentState) -> Dict[str, Any]:
        tool_map = {"bar_chart": create_bar_chart, "histogram": create_histogram}
        tool_func = tool_map.get(state["intent"])
        if not tool_func: return {"error": f"Tool for intent '{state['intent']}' not found."}
        try:
            result = tool_func(df=state["dataframe"], **state["tool_params"])
            return {"execution_result": result}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    def replan_node(self, state: AgentState) -> Dict[str, Any]:
        prompt = f"""You are a Re-Planner AI. A previous attempt failed. Your job is to create a new, simplified plan.
**Analyze:** 1. Original Request: "{state['user_prompt']}" 2. Error: "{state['error']}"
**Task:** Decide on a new `intent` and a new `user_prompt` to try next.
Respond with a single, valid JSON object with two keys: "intent" and "user_prompt".
Example: {{"intent": "code_generator", "user_prompt": "Calculate the average of the 'flat_price' column."}}"""
        try:
            structured_llm = self.llm.with_structured_output({"intent": str, "user_prompt": str})
            response = structured_llm.invoke(prompt)
            return {"intent": response['intent'], "user_prompt": response['user_prompt'], "error": ""}
        except Exception:
            return {"error": "Failed to create a new plan."}

    def decide_after_code_execution(self, state: AgentState) -> str:
        if state.get("error"):
            return "re-plan" if state.get("retries", 0) < self.MAX_RETRIES else "end_with_error"
        return "generate_response"

    def code_generator_node(self, state: AgentState) -> Dict[str, str]:
        error_context = f"The previous attempt failed: --- {state['error']} ---. Please create a new, corrected response." if state.get("error") else ""
        if state['intent'] == 'dashboard':
            # --- THIS IS THE NEW, STRICTER PROMPT ---
            prompt_template = f"""You are a world-class Data Analyst AI. Your task is to generate Python code that creates a comprehensive dashboard with multiple visualizations.

**CRITICAL RULES:**
1.  A "dashboard" is defined as a collection of **AT LEAST 3-4 DIVERSE VISUALIZATIONS.** Do not generate a single chart.
2.  Your final output **MUST** be a Python dictionary assigned to a variable named `result`.
3.  The dictionary **MUST** contain multiple keys, where each key is a descriptive string for a chart, and each value is a Plotly Figure object.
4.  Analyze the data from different angles. Create a variety of charts (e.g., histograms for distributions, bar charts for categories, scatter plots for relationships).
5.  **DO NOT** invent column names. Only use columns from the Data Summary.
6.  **DO NOT** use `import` statements. `pandas as pd` and `plotly.express as px` are already available.

**Data Summary:** ```{state['data_summary']}```
{error_context}
**User Prompt:** "{state['user_prompt']}"

**Example of an EXCELLENT final code structure:**
```python
fig1 = px.histogram(df, x='some_numeric_column', title='Distribution of [Column Name]')
fig2 = px.bar(df, x='some_categorical_column', title='Count of [Column Name]')
fig3 = px.scatter(df, x='column_a', y='column_b', title='[Column A] vs [Column B]')

result = {{
    "distribution_chart": fig1,
    "category_count_chart": fig2,
    "correlation_chart": fig3
}}
```
Now, write the Python code block to generate the dashboard components."""
        else:
            prompt_template = f"""You are a Python data scientist. Write a single Python code block to analyze the DataFrame `df`.
**RULES:**
1. The result MUST be in a variable named `result`.
2. **CRITICAL: Do NOT include `import` statements.** `pandas as pd` and `plotly.express as px` are already available.
**Data Summary:** ```{state['data_summary']}```
{error_context}
**User Prompt:** "{state['user_prompt']}"
```python
# Your code starts here.
```"""
        try:
            response = self.llm.invoke(prompt_template)
            return {"code_string": response.content.strip(), "retries": state.get("retries", 0) + 1}
        except Exception as e:
            return {"error": f"Generation failed: {e}"}

    def code_executor_node(self, state: AgentState) -> Dict[str, Any]:
        code_match = re.search(r"```python\n(.*?)```", state["code_string"], re.DOTALL)
        code = code_match.group(1).strip() if code_match else state["code_string"]
        if not code: return {"error": "No Python code was generated."}
        try:
            local_scope = {'df': self.df, 'pd': pd, 'px': px}
            exec(code, {}, local_scope)
            return {"execution_result": local_scope.get('result'), "error": ""}
        except Exception as e:
            return {"error": f"Code execution failed: {str(e)}"}

    def response_generator_node(self, state: AgentState) -> Dict[str, Dict]:
        result = state.get("execution_result")
        final_response = {}


        if isinstance(result, list) and all('plotly.graph_objs._figure.Figure' in str(type(item)) for item in result):
            final_response["plotly_dashboard"] = result
            final_response["response_text"] = "I have generated the dashboard for you."


        elif isinstance(result, dict):
            figures = [v for v in result.values() if 'plotly.graph_objs._figure.Figure' in str(type(v))]
            if figures:
                final_response["plotly_dashboard"] = figures
                final_response["response_text"] = "Here is the dashboard you requested."
                other_data = {k: v for k, v in result.items() if 'plotly.graph_objs._figure.Figure' not in str(type(v))}
                if other_data:
                    final_response["response_text"] += "\n\n**Additional Analysis:**\n"
                    for key, val in other_data.items():
                        final_response["response_text"] += f"\n**{key.replace('_', ' ').title()}**\n```\n{str(val)}\n```\n"
            elif "plotly_fig" in result:
                final_response["plotly_fig"] = result["plotly_fig"]
                final_response["response_text"] = "Here is the chart you requested."
            else:
                final_response["response_text"] = "Here is the analysis result:\n```\n" + json.dumps(result, indent=2) + "\n```"


        elif 'plotly.graph_objs._figure.Figure' in str(type(result)):
            final_response["plotly_fig"] = result
            final_response["response_text"] = "Here is the chart you requested."
        elif isinstance(result, pd.DataFrame):
            final_response["dataframe"] = result
            final_response["response_text"] = "Here is the resulting data."
        elif result is not None:
            final_response["response_text"] = str(result)
        else:
            final_response["response_text"] = "I have processed your request, but there was no specific output to display."


        try:
            suggester_llm = self.llm.bind_tools(tools=[FollowUp])
            prompt = f"""Generate 2-3 concise follow-up questions. Data Summary: {self.data_summary}. User's last prompt: "{state['user_prompt']}". Generated Answer: {final_response.get("response_text", "A chart or data was generated.")}"""
            response = suggester_llm.invoke(prompt)
            if response.tool_calls:
                final_response["follow_up_questions"] = response.tool_calls[0]['args'].get('questions', [])
            else: final_response["follow_up_questions"] = []
        except Exception:
            final_response["follow_up_questions"] = []

        return {"final_response": final_response}








