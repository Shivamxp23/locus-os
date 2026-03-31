from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    QDRANT_URL: str = "http://qdrant:6333"
    NEO4J_URL: str = "bolt://neo4j:7687"
    NEO4J_PASSWORD: str = ""
    OLLAMA_URL: str = "http://ollama:11434"
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    NOTION_CLIENT_ID: str = ""
    NOTION_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "https://api.locusapp.online/auth/google/callback"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ENVIRONMENT: str = "production"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
