from typing import TypedDict, Annotated, Optional
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from api.config import settings, SYSTEM_PROMPT, GUARDRAIL_PROMPT, FINANCIAL_DOMAINS

class State(TypedDict):
    messages: Annotated[list[AIMessage | HumanMessage], add_messages]
    financial_domain: Optional[FINANCIAL_DOMAINS]
    domain_confidence: Optional[float]
    reasoning: Optional[str]
    
class GuardrailOutput(BaseModel):
    financial_domain: FINANCIAL_DOMAINS
    domain_confidence: float
    reasoning: str
        
model = init_chat_model(
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
    model_provider="openai",
    configurable_fields=["model", "api_key", "base_url"],
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
        [SystemMessage(content=GUARDRAIL_PROMPT)] + state["messages"], 
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
        

def decide_next_node(guardrail_output: GuardrailOutput) -> bool:
    """
    Decides the next node based on the guardrail output.
    If the confidence is above a certain threshold, proceed to the agent node.
    Otherwise, end the graph execution.
    """
    if guardrail_output.domain_confidence <= 0.25:
        return False
    else:
        return True

def call_model(state: State, config: RunnableConfig) -> State:
    response = model.invoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"], config=config)
    return {"messages": [response]}
    
builder = StateGraph(State)
builder.add_node("guardrail", guardrail_node)
builder.add_node("guardrail_end", guardrail_end_node)
builder.add_node("agent", call_model)
builder.set_entry_point("guardrail")
builder.add_conditional_edges(
    "guardrail", 
    decide_next_node, 
    {False: "guardrail_end", True: "agent"})
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