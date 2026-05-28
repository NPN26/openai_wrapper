from typing import TypedDict, Annotated
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from api.config import settings, SYSTEM_PROMPT

class State(TypedDict):
    messages: Annotated[list[AIMessage | HumanMessage], add_messages]
        
model = init_chat_model(
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
    model_provider="openai",
    configurable_fields=["model", "api_key", "base_url"],
)

def call_model(state: State, config: RunnableConfig) -> State:
    response = model.invoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"], config=config)
    return {"messages": [response]}
    
builder = StateGraph(State)
builder.add_node("agent", call_model)
builder.set_entry_point("agent")
builder.add_edge("agent",END)

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