from pydantic_settings import BaseSettings
from typing import List


class AppSettings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_GPU_URL: str = "http://100.95.92.117:9001"
    DATABASE_URL: str = "sqlite:///./data/onequeue.db"
    DATA_DIR: str = "./data"
    LOG_LEVEL: str = "INFO"
    POLLING_INTERVAL_SECONDS: float = 1.0
    NVIDIA_API_KEY: str = ""
    NVIDIA_API_KEYS: str = ""
    PREFER_LOCAL_GPU: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_nvidia_keys(self) -> List[str]:
        keys: List[str] = []
        if self.NVIDIA_API_KEYS:
            keys = [k.strip() for k in self.NVIDIA_API_KEYS.split(",") if k.strip()]
        if not keys and self.NVIDIA_API_KEY:
            keys = [self.NVIDIA_API_KEY.strip()]
        return keys


settings = AppSettings()
