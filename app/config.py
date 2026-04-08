from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DATABASE_URL: str = "sqlite:///./data/onequeue.db"
    LOG_LEVEL: str = "INFO"
    POLLING_INTERVAL_SECONDS: float = 1.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = AppSettings()
