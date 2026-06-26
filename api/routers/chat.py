from datetime import datetime
from contextlib import nullcontext
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tracers.context import tracing_v2_enabled
from langsmith import Client
from api.services.graph import get_graph
from api.config import DEFAULT_MODEL, OPENAI_BASE_URL
from sqlmodel import Session, select
from api.database import engine
from api.services.models import ConversationSession, ChatMessage

router = APIRouter(prefix="/api", tags=["chat"])

# ── Request / Response models ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    thread_id: str
    message: str
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = OPENAI_BASE_URL
    langsmith_api_key: str | None = None
    langsmith_api_url: str | None = None
    langsmith_workspace_id: str | None = None
    langsmith_project: str | None = None

class MessageOut(BaseModel):
    role: str   # "user" | "assistant"
    content: str

class ChatResponse(BaseModel):
    reply: str
    thread_id: str

# ── Helpers ────────────────────────────────────────────────────────────────

def _extract_content(msg) -> str:
    """Mirrors your response_to_text() from Streamlit."""
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    return str(content).strip()

def _make_config(thread_id: str, req: ChatRequest) -> RunnableConfig:
    """Mirrors the config dict you built in Streamlit."""
    return {
        "configurable": {
            "thread_id": thread_id,
            "model": req.model or DEFAULT_MODEL,
            "api_key": req.api_key,
            "base_url": req.base_url or OPENAI_BASE_URL,
        },
        "metadata": {
            "created_at": datetime.now().isoformat()
        }
    }


def _langsmith_context(req: ChatRequest):
    api_key = (req.langsmith_api_key or "").strip()
    api_url = (req.langsmith_api_url or "").strip()
    workspace_id = (req.langsmith_workspace_id or "").strip()
    project_name = (req.langsmith_project or "").strip()

    if not api_key and not api_url and not workspace_id and not project_name:
        return nullcontext()

    if not project_name:
        project_name = "openai_wrapper"

    client_kwargs = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    if api_url:
        client_kwargs["api_url"] = api_url
    if workspace_id:
        client_kwargs["workspace_id"] = workspace_id

    client = Client(**client_kwargs) if client_kwargs else None

    return tracing_v2_enabled(project_name=project_name, client=client)

def _delete_all_threads_fast(checkpointer) -> bool:
    """Fast-path delete for Postgres-backed checkpointers."""
    try:
        from langgraph.checkpoint.postgres.base import BasePostgresSaver
    except Exception:
        return False

    if not isinstance(checkpointer, BasePostgresSaver):
        return False

    conn = getattr(checkpointer, "conn", None)
    if conn is None:
        return False

    if hasattr(conn, "connection"):
        with conn.connection() as db:
            with db.cursor() as cur:
                cur.execute("DELETE FROM checkpoint_writes")
                cur.execute("DELETE FROM checkpoint_blobs")
                cur.execute("DELETE FROM checkpoints")
        return True

    if hasattr(conn, "cursor"):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM checkpoint_writes")
            cur.execute("DELETE FROM checkpoint_blobs")
            cur.execute("DELETE FROM checkpoints")
        return True

    return False

# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Send a message and get a reply. Mirrors graph.invoke() in Streamlit."""
    graph = get_graph()
    config: RunnableConfig = _make_config(req.thread_id, req)

    with Session(engine) as db:
        # 1. GET OR CREATE SESSION (Audit/Business Logic)
        session = db.get(ConversationSession, req.thread_id)
        if not session:
            session = ConversationSession(
                id=req.thread_id, 
                user_id="default_user", # TODO: Replace with actual authenticated user
                created_by="system"
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        # 2. LOG USER MESSAGE IMMEDIATELY
        user_msg = ChatMessage(
            session_id=req.thread_id,
            role="user",
            content=req.message,
            message_order=session.turn_count * 2 + 1
        )
        db.add(user_msg)
        db.commit()

        # 3. INVOKE LANGGRAPH (Engine Logic)
        try:
            with _langsmith_context(req):
                result = graph.invoke(
                    {"messages": [HumanMessage(content=req.message)]},
                    config=config,
                )
        except Exception as exc:
            # Fail-safe: If the graph crashes, log the error so the audit trail isn't broken
            error_msg = ChatMessage(session_id=req.thread_id, role="system", content=f"System Error: {str(exc)}")
            db.add(error_msg)
            db.commit()
            error = str(exc)
            if "Malformed identifier" in error:
                error += " Use the Azure deployment name in the Model field."
            raise HTTPException(status_code=500, detail=error)

        # 4. EXTRACT METADATA FOR CUSTOM DB
        ai_msg = result["messages"][-1]
        reply = _extract_content(ai_msg)
        audit_logs = result.get("audit_tool_calls", [])
        domain = result.get("financial_domain")
        rewritten_query = result.get("rewritten_query")
        confidence = result.get("domain_confidence")

        # 5. LOG AI MESSAGE & METADATA
        ai_db_msg = ChatMessage(
            session_id=req.thread_id,
            role="assistant",
            content=reply,
            message_order=session.turn_count * 2 + 2,
            chat_metadata={"tool_audit": audit_logs},
            routed_to=str(domain) if domain else None
        )
        db.add(ai_db_msg)

        # 7. UPDATE SESSION STATS
        session.turn_count += 1
        db.commit()

        return ChatResponse(reply=reply, thread_id=req.thread_id)


@router.get("/chat/{thread_id}/history", response_model=list[MessageOut])
def get_history(thread_id: str):
    """
    Load prior messages for a thread.
    than parsing LangGraph's internal state dictionary.
    """
    with Session(engine) as db:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == thread_id)
            .order_by(ChatMessage.message_order)
        )
        messages = db.exec(statement).all()
        
        result = []
        for msg in messages:
            if msg.role in ("user", "assistant"):
                result.append(MessageOut(role=msg.role, content=msg.content))
        return result


# @router.post("/chat/stream")
# def chat_stream(req: ChatRequest):
#     """Streaming version - token by token, for a typewriter effect on the frontend."""
#     graph = get_graph()
#     config: RunnableConfig = _make_config(req.thread_id, req)

#     def token_generator():
#         with _langsmith_context(req):
#             for event in graph.stream(
#                 {"messages": [HumanMessage(content=req.message)]},
#                 config=config,
#                 stream_mode="messages",
#             ):
#                 # stream_mode="messages" yields (message_chunk, metadata) tuples
#                 message_chunk, _ = event if isinstance(event, tuple) else (event, {})
#                 token = getattr(message_chunk, "content", "")
#                 if token:
#                     yield token

#     return StreamingResponse(token_generator(), media_type="text/plain")

@router.get("/chats")
def list_chats():
    """
    Retrieve the list of all thread IDs.
    NOW READS FROM CUSTOM DB: Gives you actual Session Titles, Turn Counts, 
    and User IDs instead of raw Checkpoint thread IDs.
    """
    with Session(engine) as db:
        statement = select(ConversationSession).order_by(ConversationSession.created_at.desc())
        sessions = db.exec(statement).all()
        
        return [
            {
                "threadId": s.id, 
                "createdAt": s.created_at.isoformat() if s.created_at else None,
                "title": f"Session {s.created_at.isoformat()}" if s.created_at else None,
                "turn_count": s.turn_count
            } 
            for s in sessions
        ]

    
@router.delete("/chat/{thread_id}")
def delete_chat(thread_id: str):
    """Delete a thread from BOTH LangGraph and Custom DB."""
    graph = get_graph()
    checkpointer = getattr(graph, "checkpointer", None)
    
    # 1. Delete from LangGraph Memory
    if checkpointer:
        try:
            checkpointer.delete_thread(thread_id)
        except Exception:
            pass # Ignore if not found in LG
            
    # 2. Delete from Custom DB (Cascade will delete ChatMessages and NLP Tasks)
    with Session(engine) as db:
        session = db.get(ConversationSession, thread_id)
        if session:
            db.delete(session)
            db.commit()
            
    return {"detail": f"Thread {thread_id} deleted"}


@router.delete("/chats")
def delete_all_chats():
    """Delete all threads from BOTH LangGraph and Custom DB."""
    graph = get_graph()
    checkpointer = getattr(graph, "checkpointer", None)
    
    if checkpointer:
        _delete_all_threads_fast(checkpointer)
            
    with Session(engine) as db:
        sessions = db.exec(select(ConversationSession)).all()
        for s in sessions:
            db.delete(s)
        db.commit()
        
    return {"detail": "All threads deleted"}