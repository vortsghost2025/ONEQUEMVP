from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_GPU_URL: str = (
        "http://100.95.92.117:9001"  # Local PC via Tailscale (your RTX 5060)
    )
    DATABASE_URL: str = "sqlite:///./data/onequeue.db"
    DATA_DIR: str = "./data"
    LOG_LEVEL: str = "INFO"
    POLLING_INTERVAL_SECONDS: float = 1.0
    NVIDIA_API_KEY: str = ""
    PREFER_LOCAL_GPU: bool = True  # Route to local GPU when available

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = AppSettings()
