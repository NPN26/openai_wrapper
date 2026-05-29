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

    try:
        with _langsmith_context(req):
            result = graph.invoke(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
            )
        reply = _extract_content(result["messages"][-1])
        return ChatResponse(reply=reply, thread_id=req.thread_id)
    except Exception as exc:
        error = str(exc)
        if "Malformed identifier" in error:
            error += " Use the Azure deployment name in the Model field."
        raise HTTPException(status_code=500, detail=error)


@router.get("/chat/{thread_id}/history", response_model=list[MessageOut])
def get_history(thread_id: str):
    """
    Load prior messages for a thread.
    Mirrors graph.get_state(config).values.get("messages", []) in Streamlit.
    """
    graph = get_graph()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph.get_state(config)
        messages = snapshot.values.get("messages", [])
    except Exception:
        messages = []

    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append(MessageOut(role="user", content=_extract_content(msg)))
        elif isinstance(msg, AIMessage):
            result.append(MessageOut(role="assistant", content=_extract_content(msg)))
    return result


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Streaming version - token by token, for a typewriter effect on the frontend."""
    graph = get_graph()
    config: RunnableConfig = _make_config(req.thread_id, req)

    def token_generator():
        with _langsmith_context(req):
            for event in graph.stream(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
                stream_mode="messages",
            ):
                # stream_mode="messages" yields (message_chunk, metadata) tuples
                message_chunk, _ = event if isinstance(event, tuple) else (event, {})
                token = getattr(message_chunk, "content", "")
                if token:
                    yield token

    return StreamingResponse(token_generator(), media_type="text/plain")

@router.get("/chats")
def list_chats():
    """Retrieve the list of all thread IDs."""
    try:
        graph = get_graph()
        checkpointer = getattr(graph, "checkpointer", None)
        if not checkpointer:
            return []

        seen: set[str] = set()
        threads: list[str] = []
        for item in checkpointer.list(None):
            thread_id = (
                item.config.get("configurable", {}).get("thread_id")
                if isinstance(item.config, dict)
                else None
            )
            if thread_id and thread_id not in seen:
                seen.add(thread_id)
                threads.append(thread_id)

        return [{"threadId": thread_id} for thread_id in threads if thread_id]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    
@router.delete("/chat/{thread_id}")
def delete_chat(thread_id: str):
    """Delete a thread."""
    try:
        graph = get_graph()
        checkpointer = getattr(graph, "checkpointer", None)
        if not checkpointer:
            raise HTTPException(status_code=404, detail="No checkpointer configured")

        checkpointer.delete_thread(thread_id)
        return {"detail": f"Thread {thread_id} deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/chats")
def delete_all_chats():
    """Delete all threads."""
    try:
        graph = get_graph()
        checkpointer = getattr(graph, "checkpointer", None)
        if not checkpointer:
            raise HTTPException(status_code=404, detail="No checkpointer configured")

        if _delete_all_threads_fast(checkpointer):
            return {"detail": "All threads deleted"}

        seen: set[str] = set()
        for item in checkpointer.list(None):
            thread_id = (
                item.config.get("configurable", {}).get("thread_id")
                if isinstance(item.config, dict)
                else None
            )
            if thread_id and thread_id not in seen:
                checkpointer.delete_thread(thread_id)
                seen.add(thread_id)

        return {"detail": "All threads deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))