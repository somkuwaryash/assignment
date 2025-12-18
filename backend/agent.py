"""
Production-grade LangGraph agent for NYC 311 data analysis
"""
import pandas as pd
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
from tools import DataAnalysisTools

class AgentState(TypedDict):
    """State for the agent workflow"""
    query: str
    dataset_context: str
    analysis_plan: str
    pandas_code: str
    execution_result: dict
    needs_visualization: bool
    visualization_code: str
    visualization_image: str
    visualization_error: str
    visualization_retry_count: int
    response: str
    error: str
    retry_count: int

class NYC311AnalyticsAgent:
    """Production-grade analytics agent using LangGraph"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.tools = DataAnalysisTools(df)
        
        # Initialize DeepSeek LLM
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
            temperature=0.1,
            max_tokens=2000
        )
        
        # Build workflow graph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("plan_analysis", self.plan_analysis)
        workflow.add_node("generate_code", self.generate_code)
        workflow.add_node("execute_code", self.execute_code)
        workflow.add_node("retry_code", self.retry_code)
        workflow.add_node("decide_visualization", self.decide_visualization)
        workflow.add_node("generate_visualization", self.generate_visualization)
        workflow.add_node("retry_visualization", self.retry_visualization)
        workflow.add_node("format_response", self.format_response)
        
        # Define edges
        workflow.set_entry_point("plan_analysis")
        workflow.add_edge("plan_analysis", "generate_code")
        workflow.add_edge("generate_code", "execute_code")
        
        # Conditional edge: retry if execution fails
        workflow.add_conditional_edges(
            "execute_code",
            self.should_retry,
            {
                "retry": "retry_code",
                "continue": "decide_visualization"
            }
        )
        
        workflow.add_edge("retry_code", "execute_code")
        
        # Conditional edge: create visualization only if needed
        workflow.add_conditional_edges(
            "decide_visualization",
            self.should_visualize,
            {
                "visualize": "generate_visualization",
                "skip": "format_response"
            }
        )
        
        # Conditional edge: retry visualization if it fails
        workflow.add_conditional_edges(
            "generate_visualization",
            self.should_retry_visualization,
            {
                "retry": "retry_visualization",
                "continue": "format_response"
            }
        )
        
        workflow.add_edge("retry_visualization", "generate_visualization")
        workflow.add_edge("format_response", END)
        
        return workflow.compile()
    
    def plan_analysis(self, state: AgentState) -> AgentState:
        """Step 1: Understand query and plan analysis approach"""
        
        dataset_context = self.tools.get_dataset_context()
        
        messages = [
            SystemMessage(content=f"""You are an expert data analyst specializing in NYC 311 service request data.

DATASET INFORMATION:
{dataset_context}

Your task: Analyze the user's question and create a clear, step-by-step analysis plan.

Consider:
1. What columns are needed?
2. What aggregations/calculations are required?
3. Are there any data cleaning steps needed?
4. What's the best way to present the results?

Provide a concise but complete analysis plan."""),
            HumanMessage(content=f"User Question: {state['query']}")
        ]
        
        response = self.llm.invoke(messages)
        state["analysis_plan"] = response.content
        state["dataset_context"] = dataset_context
        state["retry_count"] = 0
        state["visualization_retry_count"] = 0
        state["needs_visualization"] = False
        state["visualization_error"] = ""
        
        return state
    
    def generate_code(self, state: AgentState) -> AgentState:
        """Step 2: Generate pandas code based on the plan"""
        
        messages = [
            SystemMessage(content=f"""You are an expert Python programmer specializing in pandas data analysis.

DATASET CONTEXT:
{state['dataset_context']}

ANALYSIS PLAN:
{state['analysis_plan']}

Generate clean, efficient pandas code to execute this analysis.

CRITICAL REQUIREMENTS:
1. The DataFrame is available as 'df' (already imported)
2. pandas is imported as 'pd'
3. MUST store final result in variable named 'result'
4. Handle missing/null values appropriately
5. Use efficient pandas operations
6. Add comments explaining complex operations
7. Return ONLY the Python code, no explanations

EXAMPLE FORMAT:
```python
# Filter data for specific condition
filtered_df = df[df['Status'].notna()]

# Calculate top 10 complaint types
result = filtered_df['Complaint Type'].value_counts().head(10)
```

Generate the code now:"""),
            HumanMessage(content=f"User Query: {state['query']}")
        ]
        
        response = self.llm.invoke(messages)
        
        # Extract code
        code = response.content
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
        
        state["pandas_code"] = code.strip()
        return state
    
    def execute_code(self, state: AgentState) -> AgentState:
        """Step 3: Execute the generated pandas code"""
        
        execution_result = self.tools.execute_pandas_code(state["pandas_code"])
        state["execution_result"] = execution_result
        
        if not execution_result["success"]:
            state["error"] = execution_result["error"]
        else:
            state["error"] = ""
        
        return state
    
    def should_retry(self, state: AgentState) -> Literal["retry", "continue"]:
        """Decide whether to retry code generation"""
        if state["error"] and state["retry_count"] < 2:
            return "retry"
        return "continue"
    
    def retry_code(self, state: AgentState) -> AgentState:
        """Step 3b: Retry code generation with error feedback"""
        
        state["retry_count"] += 1
        
        messages = [
            SystemMessage(content=f"""The previous code failed. Fix the error and generate corrected code.

PREVIOUS CODE:
```python
{state['pandas_code']}
```

ERROR:
{state['error']}

DATASET CONTEXT:
{state['dataset_context']}

Generate CORRECTED Python code that:
1. Fixes the error
2. Handles edge cases
3. Still stores result in 'result' variable

Return ONLY the corrected Python code:"""),
            HumanMessage(content="Generate the corrected code now.")
        ]
        
        response = self.llm.invoke(messages)
        
        # Extract code
        code = response.content
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
        
        state["pandas_code"] = code.strip()
        return state
    
    def decide_visualization(self, state: AgentState) -> AgentState:
        """Step 4: Decide if visualization is needed"""
        
        if state["error"]:
            state["needs_visualization"] = False
            return state
        
        messages = [
            SystemMessage(content="""You are a data visualization expert. Decide if a chart/graph would enhance understanding.

CREATE VISUALIZATION whenever the data is visual in nature:
✓ Top N lists, rankings, comparisons
✓ Trends over time, distributions
✓ Geographic patterns, categorical breakdowns
✓ Any multi-value results that benefit from visual representation

DO NOT create visualization ONLY if:
✗ User explicitly says "no chart", "just numbers", "text only"
✗ Single scalar values (e.g., "what is the total count?" → just one number)
✗ Yes/no answers
✗ Results would be completely unreadable as a chart

DEFAULT: When in doubt, CREATE the visualization. Most queries benefit from visual representation.

Respond with ONLY 'YES' or 'NO'."""),
            HumanMessage(content=f"""User Query: {state['query']}

Result Type: {state['execution_result'].get('result_type')}
Result Preview: {str(state['execution_result'].get('result'))[:200]}

Should we create a visualization? Answer YES or NO only.""")
        ]
        
        response = self.llm.invoke(messages)
        decision = response.content.strip().upper()
        
        state["needs_visualization"] = "YES" in decision
        
        return state
    
    def should_visualize(self, state: AgentState) -> Literal["visualize", "skip"]:
        """Router: decide visualization path"""
        if state["needs_visualization"] and not state["error"]:
            return "visualize"
        return "skip"
    
    def generate_visualization(self, state: AgentState) -> AgentState:
        """Step 5: Generate and execute visualization code"""
        
        # Get the actual pandas code that was executed
        pandas_code = state["pandas_code"]
        
        # Build the prompt based on whether this is a retry
        if state["visualization_retry_count"] > 0:
            system_message = f"""You are a data visualization expert. The previous visualization code FAILED with an error.

PREVIOUS VISUALIZATION CODE THAT FAILED:
```python
{state['visualization_code']}
```

ERROR MESSAGE:
{state['visualization_error']}

ORIGINAL ANALYSIS CODE (that worked successfully):
```python
{pandas_code}
```

ANALYSIS RESULT TYPE: {state['execution_result'].get('result_type')}
RESULT PREVIEW:
{state['execution_result']['result'][:500]}

FIX THE ERROR and generate corrected visualization code.

CRITICAL REQUIREMENTS:
1. DO NOT use column names that don't exist in the DataFrame
2. You MUST re-execute the EXACT working analysis code first
3. DO NOT create intermediate DataFrames with new column names
4. Use the actual result from re-executing the analysis
5. Available in namespace: pd, np, df, plt, sns
6. Create figure: fig, ax = plt.subplots(figsize=(12, 7))
7. End with plt.tight_layout()

CORRECT APPROACH:
```python
# Re-execute the working analysis (copy-paste from above)
result_data = df['Complaint Type'].value_counts().head(10)

# Plot directly - no intermediate variables with new names
fig, ax = plt.subplots(figsize=(12, 7))
result_data.plot(kind='barh', ax=ax, color='steelblue')
ax.set_xlabel('Count')
ax.set_title('Top 10 Complaint Types')
plt.tight_layout()
```

Generate ONLY the CORRECTED visualization code:"""
        else:
            system_message = f"""You are a data visualization expert using matplotlib and seaborn.

IMPORTANT: The following pandas code was already executed successfully:
```python
{pandas_code}
```

ANALYSIS RESULT TYPE: {state['execution_result'].get('result_type')}
RESULT PREVIEW:
{state['execution_result']['result'][:500]}

Generate Python code to create a professional visualization of this result.

CRITICAL REQUIREMENTS:
1. DO NOT re-import anything (plt, sns, pd, np already available)
2. DataFrame 'df' is available
3. You MUST re-execute the EXACT analysis code above to get the data object
4. DO NOT create DataFrames with new column names - use the actual data structure
5. Create figure with: fig, ax = plt.subplots(figsize=(12, 7))
6. Choose appropriate chart type:
   - Series/value_counts: horizontal bar chart (barh)
   - Time series: line chart
   - Distributions: histogram
   - Comparisons: bar chart
7. Professional styling:
   - Clear, descriptive title
   - Labeled axes with units
   - Colors: 'steelblue', 'viridis', seaborn palettes
   - Value labels where helpful
   - Grid for readability
8. End with plt.tight_layout()

EXAMPLE STRUCTURE:
```python
# Re-execute the exact analysis from above
result_data = df['Complaint Type'].value_counts().head(10)

# Create visualization directly from result_data
fig, ax = plt.subplots(figsize=(12, 7))
result_data.plot(kind='barh', ax=ax, color='steelblue')
ax.set_xlabel('Count')
ax.set_title('Top 10 Complaint Types')
plt.tight_layout()
```

Generate ONLY the visualization code:"""
        
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=f"User Query: {state['query']}\n\nCreate the visualization.")
        ]
        
        response = self.llm.invoke(messages)
        
        # Extract code
        viz_code = response.content
        if "```python" in viz_code:
            viz_code = viz_code.split("```python")[1].split("```")[0]
        elif "```" in viz_code:
            viz_code = viz_code.split("```")[1].split("```")[0]
        
        viz_code = viz_code.strip()
        state["visualization_code"] = viz_code
        
        # Execute visualization code
        result = self.tools.execute_visualization_code(viz_code)
        
        if result["success"]:
            state["visualization_image"] = result["image"]
            state["visualization_error"] = ""
        else:
            state["visualization_image"] = ""
            state["visualization_error"] = result["error"]
        
        return state
    
    def should_retry_visualization(self, state: AgentState) -> Literal["retry", "continue"]:
        """Decide whether to retry visualization generation"""
        if state["visualization_error"] and state["visualization_retry_count"] < 2:
            return "retry"
        return "continue"
    
    def retry_visualization(self, state: AgentState) -> AgentState:
        """Step 5b: Increment retry counter for visualization"""
        state["visualization_retry_count"] += 1
        return state
    
    def format_response(self, state: AgentState) -> AgentState:
        """Step 6: Format the final response"""
        
        if state["error"]:
            state["response"] = f"""I encountered an error while analyzing the data:

{state['error']}

Please try rephrasing your question or ask something else about the NYC 311 dataset."""
            return state
        
        messages = [
            SystemMessage(content="""You are a helpful data analyst presenting findings to a user.

Format the results in a clear, professional manner:
1. Start with a direct answer to their question
2. Present key findings with specific numbers
3. Add relevant context or insights
4. Use bullet points for multiple items
5. Be conversational but precise
6. If a visualization was created, reference it naturally

Do NOT:
- Include the code used
- Use technical jargon unnecessarily
- Make claims not supported by the data"""),
            HumanMessage(content=f"""User Question: {state['query']}

Analysis Results:
{state['execution_result']['result']}

Visualization Created: {state.get('needs_visualization', False) and not state.get('visualization_error')}

Format this into a clear, helpful response:""")
        ]
        
        response = self.llm.invoke(messages)
        state["response"] = response.content
        
        return state
    
    def process_query(self, query: str) -> dict:
        """
        Main entry point: Process a user query
        
        Args:
            query: User's question about the data
            
        Returns:
            Dict with 'response' and optional 'visualization'
        """
        initial_state = {
            "query": query,
            "dataset_context": "",
            "analysis_plan": "",
            "pandas_code": "",
            "execution_result": {},
            "needs_visualization": False,
            "visualization_code": "",
            "visualization_image": "",
            "visualization_error": "",
            "visualization_retry_count": 0,
            "response": "",
            "error": "",
            "retry_count": 0
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            return {
                "response": final_state["response"],
                "visualization": final_state.get("visualization_image") if final_state.get("visualization_image") else None,
                "code_executed": final_state.get("pandas_code"),
                "visualization_code": final_state.get("visualization_code") if final_state.get("visualization_image") else None,
                "success": not bool(final_state.get("error"))
            }
            
        except Exception as e:
            return {
                "response": f"An unexpected error occurred: {str(e)}",
                "visualization": None,
                "code_executed": None,
                "visualization_code": None,
                "success": False
            }