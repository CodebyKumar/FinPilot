from typing import Annotated, TypedDict, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from finpilot import config
from finpilot.tools import ALL_TOOLS
from finpilot.db.mongo import get_user

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str

# 1. Initialize the LLM and bind tools
llm = ChatOpenAI(model="gpt-4o", api_key=config.OPENAI_API_KEY, temperature=0.0)
llm_with_tools = llm.bind_tools(ALL_TOOLS)

# 2. Define the agent execution node
def call_model(state: State):
    messages = state["messages"]
    user_id = state.get("user_id", "unknown")
    
    # Enforce system prompt natively by ensuring the first message is a SystemMessage
    if not messages or not isinstance(messages[0], SystemMessage):
        user_profile = get_user(user_id) or {}
        industry = user_profile.get("industry", "Unknown")
        entity_type = user_profile.get("entity_type", "Unknown")
        turnover = user_profile.get("annual_turnover", 0.0)
        
        sys_msg = SystemMessage(
            content=f"You are FinPilot AI, a financial compliance and intelligence agent.\n"
                    f"You have access to a suite of tools to fetch expenses, profits, GST claims, and tax issues.\n"
                    f"Always use tools when asked about financial numbers, you must invoke them accurately.\n"
                    f"The current user's business context:\n"
                    f"- Industry: {industry}\n"
                    f"- Entity: {entity_type}\n"
                    f"- Turnover: ₹{turnover:,.2f}\n"
        )
        messages = [sys_msg] + messages

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 3. Compile Graph with Memory
workflow = StateGraph(State)

workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(ALL_TOOLS))

# Link the DAG
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

# Ephemeral in-memory saver for immediate thread access
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

def execute_goal(user_id: str, message: str) -> Dict[str, Any]:
    """
    Master Orchestrator execution wrapper.
    Passes the input to the compiled LangGraph agent, using user_id as the thread_id for conversational memory.
    """
    config_dict = {"configurable": {"thread_id": user_id}}
    
    # Pass the user input into the graph
    inputs = {
        "messages": [("user", message)],
        "user_id": user_id
    }
    
    final_state = app.invoke(inputs, config=config_dict)
    
    # Extract the final AI message content
    final_message = final_state["messages"][-1].content
    
    return {
        "user_id": user_id,
        "input_query": message,
        "agent_response": final_message
    }
