import os

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    LANGSMITH_TRACING: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_ENDPOINT: str = ""
    LANGSMITH_PROJECT: str = ""
    POSTGRES_URI: str = ""

settings = Settings()

os.environ["LANGSMITH_TRACING"] = settings.LANGSMITH_TRACING
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT

OPENAI_BASE_URL = "https://api.openai.com/v1"
LANGSMITH_BASE_URL = "https://api.smith.langchain.com"
DEFAULT_MODEL = "gpt-4.1"
SYSTEM_PROMPT = "You are a helpful chat assistant. Reply naturally and keep the conversation going."
