from typing import TypedDict, Annotated, Optional, Any, cast
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langchain.tools import tool
from pydantic import BaseModel, json
from sqlmodel import Session, select, text
from api.database import engine
from api.services.models import Customers, get_schema
from api.config import settings, SYSTEM_PROMPT, GUARDRAIL_PROMPT, HISTORY_PROMPT, SQL_PLAN_PROMPT, SQL_PROMPT, FINANCIAL_DOMAINS

class State(TypedDict):
    messages: Annotated[list[AIMessage | HumanMessage], add_messages]
    is_follow_up: Optional[bool]
    referenced_turn_indices: Optional[list[int]]
    financial_domain: Optional[FINANCIAL_DOMAINS]
    domain_confidence: Optional[float]
    reasoning: Optional[str]
    needs_sql: Optional[bool]
    query_intent: Optional[str]
    filters: Optional[dict[str, str]]
    sql_results: Optional[str]
    
class GuardrailOutput(BaseModel):
    financial_domain: FINANCIAL_DOMAINS
    domain_confidence: float
    reasoning: str
    
class HistoryOutput(BaseModel):
    is_follow_up: bool
    referenced_turn_indices: list[int]
    
class SQLPlannerOutput(BaseModel):
    needs_sql: bool
    query_intent: Optional[str]
    filters: Optional[dict[str, str]]
    
class SQLQueryOutput(BaseModel):
    results: Optional[str]
        
model = init_chat_model(
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
    model_provider="openai",
    configurable_fields=["model", "api_key", "base_url"],
)

@tool
def sql_db_query(sql_query: str) -> str:
    """
    Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields."""
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
def sql_db_schema() -> str:
    """
    This tool returns the database schema for the customer table, including column names and descriptions.
    Use this information to construct accurate SQL queries when the sql_db_query tool returns errors related to unknown columns or tables.
    """
    return get_schema()

tools = [sql_db_query, sql_db_schema]

# To make the agent use JSON mode, we bind the response_format to the model.
# Note: When using JSON mode, the prompt MUST include the word 'JSON'.
agent_model = model.bind(response_format={"type": "json_object"})

agent = create_agent(
    model = cast(Any, agent_model), 
    tools = tools
)

def guardrail_node(state: State, config: RunnableConfig) -> State:
    """
    Uses a tool strategy (Structured Output) to classify the user's message 
    into one of the predefined 11 financial domains.
    """
    # Bind the Pydantic schema to the model to force structured output
    structured_llm = model.with_structured_output(GuardrailOutput)
    
    # Invoke the model with the guardrail prompt and current messages
    result = structured_llm.invoke(
        [SystemMessage(content=GUARDRAIL_PROMPT), state["messages"][-1]], 
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
    
def history_node(state: State, config: RunnableConfig) -> State:
    """
    Node to determine if the current query is a follow-up that depends on prior conversation turns.
    If so, it identifies which turns are relevant to provide context to the agent.
    """
    # Bind the Pydantic schema to the model to force structured output
    structured_llm = model.with_structured_output(HistoryOutput)
    
    # Prepare the conversation history block for the prompt
    history_block = "\n".join(
        f"Turn {i}: {msg.content}" for i, msg in enumerate(state["messages"])
    )
    
    # Invoke the model with the history prompt, current messages, and conversation history
    result = structured_llm.invoke(
        [SystemMessage(content=HISTORY_PROMPT.format(history_block=history_block, current_query=state["messages"][-1].content))], 
        config=config
    )
    
    # Update the state with any relevant information about follow-up status or referenced turns
    return {
        "is_follow_up": result.is_follow_up,
        "referenced_turn_indices": result.referenced_turn_indices
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
    
def sql_planner_node(state: State, config: RunnableConfig) -> State:
    """
    Extracts the intent and relevant entities from the user's message to formulate a SQL query.
    """
    # Bind the Pydantic schema to the model to force structured output
    structured_llm = model.with_structured_output(SQLPlannerOutput)
    
    # Invoke the model with the SQL planner prompt and current messages
    result = structured_llm.invoke(
        [SystemMessage(content=SQL_PLAN_PROMPT), state["messages"][-1]], 
        config=config
    )
    return {
        "needs_sql": result.needs_sql,
        "query_intent": result.query_intent,
        "filters": result.filters
    }
    
def decide_sql_node(state: State) -> bool:
    """
    Decides whether the agent needs to generate and execute a SQL query based on the planner output.
    If needs_sql is True, proceeds to the sql_node; otherwise, goes to the agent node for a regular response.
    """
    return state.get("needs_sql") or False

def sql_node(state: State, config: RunnableConfig) -> State:
    """
    Generates and executes a SQL query based on the user's message and returns the results. With retry logic in case of SQL errors.
    """
    schema = get_schema()
    # Structure the instruction clearly as the "Human" task input
    instruction = (
        f"Based on the intent: {state.get('query_intent')} and filters: {state.get('filters')}, "
        f"generate and execute a SQL query using this schema:\n\n{schema}"
    )

    # 1. Invoke the agent. It handles the tool-calling loop (SQL generation, execution, and retries).
    # We append a JSON instruction because agent_model is bound to JSON mode.
    # The agent should return a dictionary with the structured output.
    agent_response = agent.invoke(
        {"input": instruction, "messages": [SystemMessage(content=SQL_PROMPT), HumanMessage(content=instruction)]},
        config=config
    )
    
    # Ensure agent_response is a dictionary. If it's a list of messages, extract the last message's content.
    if isinstance(agent_response, list):
        # Assuming the last message in the list contains the structured JSON output
        agent_text = agent_response[-1].content if agent_response else "{}"
    elif isinstance(agent_response, dict) and "messages" in agent_response:
        agent_text = agent_response["messages"][-1].content if agent_response["messages"] else "{}"
    elif isinstance(agent_response, dict):
        # If it's already a dict, assume it's the structured output directly
        agent_text = json.dumps(agent_response) # Convert dict to string for parser
    else:
        agent_text = str(agent_response)

    # 2. Use structured output to parse the agent's final multi-turn results into the state.
    parser = model.with_structured_output(SQLQueryOutput)
    try:
        final_result = parser.invoke(f"Extract the final database query results from this agent output: {agent_text}", config=config)
        return {"sql_results": final_result.results if final_result.results else "No results found."}
    except Exception as e:
        # Handle cases where parsing fails, e.g., if agent_text is not valid JSON
        print(f"Error parsing agent output: {e}")
        return {"sql_results": f"Error processing SQL query results: {agent_text}"}

def call_model(state: State, config: RunnableConfig) -> State:
    
    prompt_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    
    # Add the sql results to the prompt if available, so the model can use that information to answer the user's query.
    if state.get("sql_results"):
        prompt_messages.append(SystemMessage(content=f"SQL Query Results: {state['sql_results']}"))
    
    # Add the selected history turns back into the prompt if it's a follow-up question. This allows the agent to have the necessary context to answer follow-up questions correctly.
    if state.get("is_follow_up") and state.get("referenced_turn_indices"):
        # If it's a follow-up, we can choose to include the referenced turns in the prompt, which includes the user prompt and response
        referenced_messages = [
            msg
            for i in state["referenced_turn_indices"]
            if 0 <= i < len(state["messages"])
            for msg in (
                [state["messages"][i]]
                + (
                    [state["messages"][i + 1]]
                    if i + 1 < len(state["messages"])
                    and isinstance(state["messages"][i + 1], AIMessage)
                    else []
                )
            )
        ]
        # Filter: System Prompt + Only relevant history + Current user message
        prompt_messages += referenced_messages + [state["messages"][-1]]
    else:
        # If not a follow-up, only send the System Prompt and the current user message
        prompt_messages += [state["messages"][-1]]
    response = model.invoke(prompt_messages, config=config)
    return {"messages": [response]}
    
builder = StateGraph(State)
builder.add_node("guardrail", guardrail_node)
builder.add_node("guardrail_end", guardrail_end_node)
builder.add_node("agent", call_model)
builder.add_node("history", history_node)
builder.add_node("sql_planner", sql_planner_node)
builder.add_node("sql_node", sql_node)
builder.set_entry_point("guardrail")
builder.add_conditional_edges(
    "guardrail", 
    decide_next_node, 
    {   False: "guardrail_end", 
        True: "history"
})
builder.add_edge("history", "sql_planner")
builder.add_conditional_edges(
    "sql_planner", 
    decide_sql_node, 
    {   True: "sql_node", 
        False: "agent"
})
builder.add_edge("sql_node", "agent")
builder.add_edge("guardrail_end", END)
builder.add_edge("agent", END)

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