from typing import TypedDict, Annotated, Optional, Any, cast
from langchain.agents import create_agent, AgentState
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langchain.tools import tool, ToolRuntime
from pydantic import BaseModel, json
from sqlmodel import Session, select, text
from api.database import engine
from api.services.models import get_tables_summary, get_detailed_schema
from api.config import settings, SYSTEM_PROMPT, GUARDRAIL_PROMPT, FOLLOW_UP_PROMPT, REWRITER_PROMPT, COMPRESSOR_PROMPT, FINANCIAL_DOMAINS

class CustomAgentState(AgentState):
    financial_facts: Optional[list[str]]

class State(TypedDict):
    messages: Annotated[list[AIMessage | HumanMessage], add_messages]
    is_follow_up: Optional[bool]
    referenced_turn_indices: Optional[list[int]]
    financial_domain: Optional[FINANCIAL_DOMAINS]
    domain_confidence: Optional[float]
    reasoning: Optional[str]
    rewritten_query: Optional[str]
    financial_facts: Optional[list[str]]
    audit_tool_calls: Optional[list[dict[str, Any]]]
    
class followUpNodeOutput(BaseModel):
    is_follow_up: bool
    
class rewriterOutput(BaseModel):
    rewritten_query: str
    referenced_turn_indices: list[int]
    
class GuardrailOutput(BaseModel):
    financial_domain: FINANCIAL_DOMAINS
    domain_confidence: float
    reasoning: str
    
class CompressorOutput(BaseModel):
    financial_facts: list[str]

model = init_chat_model(
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
    model_provider="openai",
    configurable_fields=["model", "api_key", "base_url"],
)

@tool
def db_query(sql_query: str) -> str:
    """
    Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    If you encounter an issue with Unknown column 'xxxx' in 'field list', use db_schema to query the correct table fields."""
    
    if not sql_query.strip().upper().startswith("SELECT"):
        return "Error: only SELECT statements are permitted."
    with Session(engine) as session:
        try:
            # Wrap the raw string in text() to execute it
            statement = text(sql_query)
            result = session.exec(statement)
            
            if result:
                rows = result.all()
                return f"Query executed successfully. Number of rows returned: {len(rows)}. Results: {rows}"
        except Exception as e:
            return f"Error executing SQL query: {str(e)}"
        
@tool
def list_tables() -> str:
    """
    Returns a brief list of all available tables and their high-level descriptions.
    Use this tool FIRST to identify which tables are relevant to the user's query 
    before fetching detailed schemas.
    """
    return get_tables_summary()

@tool
def get_table_schema(table_names: list[str]) -> str:
    """
    Returns the detailed schema (columns, types, and descriptions) for specific tables.
    Input is a list of table names. ONLY request tables that are relevant to the user's 
    query to save tokens. Do not request all tables at once.
    """
    with Session(engine) as session:
        return get_detailed_schema(session, table_names)
    
@tool
def recall_financial_facts(runtime: ToolRuntime[CustomAgentState]) -> str:
    """
    Returns a summary of all financial facts that have been recorded in the current conversation.
    """
    state = cast(CustomAgentState, runtime.state)
    financial_facts = state.get("financial_facts")
    if not financial_facts:
        return "No financial facts have been recorded in this conversation."
    else:
        return "\n".join(financial_facts)

# Update your tools list
tools = [db_query, list_tables, get_table_schema, recall_financial_facts]

agent = create_agent(
    model = cast(Any,model), 
    tools = tools,
    state_schema=CustomAgentState
)

def follow_up_node(state: State, config: RunnableConfig) -> State:
    """
    This node determines if the user's current query is a follow-up question that requires context from previous conversation turns.
    """
    # Bind the Pydantic schema to the model to force structured output
    structured_llm = model.with_structured_output(followUpNodeOutput)
    
    history_block = "\n".join(
        f"{'Human' if isinstance(msg, HumanMessage) else 'AI'}: {msg.content}"
        for msg in state["messages"][:-1]
    )
    
    # Invoke the model with the rewriter prompt and the agent's error message
    result = structured_llm.invoke(
        [SystemMessage(content=FOLLOW_UP_PROMPT.format(history_block=history_block, current_query=state["messages"][-1].content))], 
        config=config
    )
    
    return {        
        "is_follow_up": result.is_follow_up,
        "rewritten_query": None,
        "referenced_turn_indices": None
    }

def history_and_rewriter_node(state: State, config: RunnableConfig) -> State:
    """
    This node combines the history and rewriter nodes to determine if the user's current query is a follow-up question that requires context from previous conversation turns.
    """
    # Bind the Pydantic schema to the model to force structured output
    structured_llm = model.with_structured_output(rewriterOutput)
    
    MAX_HISTORY_TURNS = 7
    history_messages = state["messages"][-(MAX_HISTORY_TURNS * 2 + 1):-1]
    num_complete_turns = len(history_messages) // 2
    history_messages = history_messages[:num_complete_turns*2]  # Get the last N turns (user + agent)
    
    # Prepare the conversation history block for the prompt
    history_block = "\n".join(
        f"Turn {(i // 2) + 1}: \n Human: {history_messages[i].content} \n AI: {history_messages[i+1].content}" for i in range(0, len(history_messages), 2)
    )
    
    # Invoke the model with the rewriter prompt and the agent's error message
    result = structured_llm.invoke(
        [SystemMessage(content=REWRITER_PROMPT.format(history_block=history_block, current_query=state["messages"][-1].content))], 
        config=config
    )
    
    return {
        "referenced_turn_indices": result.referenced_turn_indices,
        "rewritten_query": result.rewritten_query
    }
    

def guardrail_node(state: State, config: RunnableConfig) -> State:
    """
    Uses a tool strategy (Structured Output) to classify the user's message 
    into one of the predefined 11 financial domains.
    """
    # Bind the Pydantic schema to the model to force structured output
    structured_llm = model.with_structured_output(GuardrailOutput)
    
    # Use rewritten query if it exists; otherwise, fall back to the original message content
    query = state.get("rewritten_query") or state["messages"][-1].content

    # Invoke the model with the guardrail prompt and the rewritten query
    result = structured_llm.invoke(
        [SystemMessage(content=GUARDRAIL_PROMPT), query], 
        config=config
    )
    return {
        "financial_domain": result.financial_domain, 
        "domain_confidence": result.domain_confidence,
        "reasoning": result.reasoning
    }
    
def guardrail_end_node(state: State) -> State:
    """
    End node for cases where the guardrail determines the query is not relevant to financial domains.
    """
    return {
        "messages": state["messages"] + [AIMessage(content="Sorry, I can only assist with financial queries.")]
    } 

def decide_next_node(state: State) -> bool:
    """
    Decides the next node based on the guardrail output.
    If the confidence is above a certain threshold, proceed to the agent node.
    Otherwise, end the graph execution.
    """
    if (state.get("domain_confidence") or 0) <= 0.25:
        return False
    else:
        return True
    
def is_first_turn(state: State) -> bool:
    """
    Determines if the current turn is the first turn in the conversation.
    """
    return len(state["messages"]) == 1

def is_follow_up(state: State) -> bool:
    """
    Determines if the current turn is a follow-up turn based on the presence of previous messages.
    """
    return state.get("is_follow_up", False)

def agent_node(state: State, config: RunnableConfig) -> State:
    prompt_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    
    # Use the rewritten string if available, otherwise use the raw HumanMessage object
    user_query = state.get("rewritten_query") or state["messages"][-1]

    # Add the selected history turns back into the prompt if it's a follow-up question. This allows the agent to have the necessary context to answer follow-up questions correctly.
    if state.get("is_follow_up") and state.get("referenced_turn_indices"):
        # If it's a follow-up, we can choose to include the referenced turns in the prompt, which includes the user prompt and response
        referenced_messages = [
            msg
            for i in state["referenced_turn_indices"]
            if 1 <= i <= len(state["messages"])//2
            for msg in (
                [state["messages"][(i-1)*2]] + [state["messages"][(i-1)*2 + 1]]
            )
        ]
        # Filter: System Prompt + Only relevant history +  user prompt (which should be self-contained with necessary context)
        prompt_messages += referenced_messages + [user_query]
    else:
        # If not a follow-up, only send the System Prompt and the current user message
        prompt_messages += [user_query]

    agent_response = agent.invoke(
        {"messages": prompt_messages, "financial_facts": state.get("financial_facts", [])},
        config=config
    )
    
    audit_log = []
    for message in agent_response["messages"]:
        if isinstance(message, AIMessage) and message.tool_calls:
            for tc in message.tool_calls:
                audit_log.append({"type": "Tool_req", "tool": tc['name'], "args": tc['args']})
        elif isinstance(message, ToolMessage):
            audit_log.append({"type": "Tool_res", "tool": message.name, "result": str(message.content)[:2500]})

    return {
        "messages": [agent_response["messages"][-1]],
        "audit_tool_calls": audit_log,
        "financial_domain": state.get("financial_domain"),
        "domain_confidence": state.get("domain_confidence"),
        "rewritten_query": state.get("rewritten_query")
    }

def compressor_node(state: State, config: RunnableConfig) -> dict:
    """
    Runs AFTER the agent to update the financial facts ledger.
    """
    latest_human_message = next((msg for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)), None)
    latest_ai_message = next((msg for msg in reversed(state["messages"]) if isinstance(msg, AIMessage)), None)
    
    if not latest_human_message or not latest_ai_message:
        return {
            "domain_summary": state.get("domain_summary", {}),
            "financial_facts": state.get("financial_facts", [])
        }
    
    current_facts = state.get("financial_facts", [])
    
    facts_texts = "\n".join([f"- {f}" for f in current_facts]) if current_facts else "- None"

    prompt = COMPRESSOR_PROMPT.format(
        latest_user_message=latest_human_message.content,
        latest_agent_response=latest_ai_message.content,
        facts_text=facts_texts
    )
    
    structured_llm = model.with_structured_output(CompressorOutput)
    result = structured_llm.invoke([SystemMessage(content=prompt)], config=config)
    if result.financial_facts:
        new_facts = current_facts + result.financial_facts
    else:
        new_facts = current_facts

    return {
        "financial_facts": new_facts
    }
    

    
builder = StateGraph(State)
builder.add_node("guardrail", guardrail_node)
builder.add_node("guardrail_end", guardrail_end_node)
builder.add_node("follow_up", follow_up_node)
builder.add_node("history_and_rewriter", history_and_rewriter_node)
builder.add_node("agent", agent_node)
builder.add_node("compressor", compressor_node)

builder.add_conditional_edges(
    START,
    is_first_turn,
    {
        True: "guardrail",
        False: "follow_up"
    }
)

builder.add_conditional_edges(
    "guardrail", 
    decide_next_node, 
    {   
        False: "guardrail_end", 
        True: "agent"
    }
)

builder.add_conditional_edges(
    "follow_up", 
    is_follow_up, 
    {
        True: "history_and_rewriter", 
        False: "guardrail"
    }
)
builder.add_edge("history_and_rewriter", "guardrail")
builder.add_edge("guardrail_end", END)
builder.add_edge("agent", "compressor")
builder.add_edge("compressor", END)

_graph = None
_pool = None

def get_graph():
    global _graph, _pool
    if _graph is None:
        postgres_uri = settings.POSTGRES_URI.strip()
        if postgres_uri:
            try:
                from psycopg_pool import ConnectionPool
                from langgraph.checkpoint.postgres import PostgresSaver
            except ImportError as exc:
                raise RuntimeError(
                    "Postgres support requires psycopg with pool support. "
                    "Install psycopg[binary,pool] or unset POSTGRES_URI."
                ) from exc
            
            # Create a connection pool instead of a single connection
            _pool = ConnectionPool(
                conninfo=postgres_uri,
                max_size=20,
                min_size=0,
                max_idle=30,  # Proactively close idle connections before Neon does
                kwargs={"autocommit": True}
            )
            checkpointer = PostgresSaver(_pool)
            checkpointer.setup()
            _graph = builder.compile(checkpointer=checkpointer)
        else:
            _graph = builder.compile()
    return _graph

def close_pool():
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None