"""
OneQueue Smart Router - SIMPLE version
Only uses local Ollama on RTX 5060
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("onequeue.router")

OLLAMA_URL = "http://100.95.92.117:9001"


class TaskType(Enum):
    GENERAL = "general"
    CODE = "code"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    MATH = "math"
    CREATIVE = "creative"


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str = "ollama"
    tier: str = "fast"
    category: str = "general"
    context_length: int = 8192
    specialty: List[TaskType] = None  # type: ignore
    speed_score: int = 9
    quality_score: int = 8
    cost_tier: str = "free"

    def __post_init__(self):
        if self.specialty is None:
            self.specialty = [TaskType.GENERAL]


class SmartRouter:
    def __init__(self):
        self.models: Dict[str, ModelInfo] = {}
        self._load_models()

    def _load_models(self):
        """Load models from local Ollama"""
        try:
            import httpx

            resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10.0)
            if resp.status_code == 200:
                ollama_models = resp.json().get("models", [])
                for m in ollama_models:
                    model_id = m.get("name", "")
                    if model_id:
                        self.models[model_id] = ModelInfo(
                            id=model_id,
                            name=model_id.replace(":latest", "")
                            .replace("-instruct", "")
                            .title(),
                        )
                logger.info(f"Loaded {len(self.models)} models from Ollama")
        except Exception as e:
            logger.warning(f"Ollama not reachable: {e}")
            self.models["llama3:latest"] = ModelInfo(id="llama3:latest", name="Llama 3")

    def list_models(self) -> Dict[str, ModelInfo]:
        return self.models

    def get_best_model(self, prompt: str = "") -> str:
        """Get best model - just return first available"""
        if not self.models:
            return "llama3:latest"
        if "llama3:latest" in self.models:
            return "llama3:latest"
        return list(self.models.keys())[0]

    def get_model_info(self, model_id: str) -> ModelInfo:
        return self.models.get(model_id) or ModelInfo(id=model_id, name=model_id)

    # === Methods needed by other files ===
    def select_model(
        self, prompt: str, preferred_model: Optional[str] = None
    ) -> Tuple[str, ModelInfo]:
        """Select best model for prompt"""
        if preferred_model and preferred_model in self.models:
            return preferred_model, self.models[preferred_model]
        model_id = self.get_best_model(prompt)
        return model_id, self.models.get(model_id) or ModelInfo(
            id=model_id, name=model_id
        )

    def analyze_task(self, prompt: str) -> TaskType:
        """Analyze task type from prompt"""
        prompt_lower = prompt.lower()
        if re.search(r"\b(code|function|def|import|python|javascript)\b", prompt_lower):
            return TaskType.CODE
        if re.search(r"\b(math|calculate|equation|derivative)\b", prompt_lower):
            return TaskType.MATH
        if re.search(r"\breason|analyze|think|explain|why|how\b", prompt_lower):
            return TaskType.REASONING
        if re.search(r"\bwrite|story|poem|creative|imagine\b", prompt_lower):
            return TaskType.CREATIVE
        return TaskType.GENERAL

    def get_fallback_chain(self, model_id: str) -> List[str]:
        """Return fallback chain"""
        chain = [model_id]
        if "llama3:latest" not in chain:
            chain.append("llama3:latest")
        return chain

    def get_recommended_models(self, task_type: TaskType, limit: int = 5) -> List[str]:
        """Get recommended models"""
        return list(self.models.keys())[:limit]

    def list_models_by_specialty(self, task_type: TaskType) -> List[ModelInfo]:
        """List models by specialty"""
        return list(self.models.values())

    def _is_nvidia_model(self, model_id: str) -> bool:
        """Check if NVIDIA model"""
        return "/" in model_id
