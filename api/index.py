from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import chat, validate
from .services.graph import get_graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_graph()
    yield

app = FastAPI(title="OpenAI Wrapper API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(validate.router)