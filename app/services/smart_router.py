"""
Smart Model Router for OneQueue
Intelligently selects the best model based on task requirements
"""

import re
import asyncio
import httpx
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging

from app.config import settings
from app.services.nvidia_api import pool as nvidia_key_pool

logger = logging.getLogger("onequeue.router")


class TaskType(Enum):
    """Categorize task types for model selection"""

    CODE = "code"
    MATH = "math"
    REASONING = "reasoning"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    GENERAL = "general"
    LONG_CONTEXT = "long_context"
    MULTILINGUAL = "multilingual"


@dataclass
class ModelInfo:
    """Model metadata for routing decisions"""

    id: str
    name: str
    provider: str  # "nvidia" or "ollama"
    tier: str  # "flagship", "fast", "coding", "reasoning"
    category: str
    context_length: int
    specialty: List[TaskType]
    speed_score: int  # 1-10 (10 = fastest)
    quality_score: int  # 1-10 (10 = best)
    cost_tier: str  # "free", "low", "medium", "high"


class SmartRouter:
    """Intelligent model selection based on task analysis"""

    def __init__(self):
        self.models = self._initialize_model_registry()
        self.benchmarks: Dict[str, Dict] = {}

        # Model auto-detection
        self._available_ollama_models: List[str] = []
        self._available_nvidia_models: List[str] = []
        self._detection_cache_ttl = timedelta(seconds=60)
        self._last_detection: Optional[datetime] = None

        # NVIDIA API settings

    def _is_nvidia_model(self, model_id: str) -> bool:
        """Check if model is from NVIDIA"""
        if model_id in self.models:
            return self.models[model_id].provider == "nvidia"
        return "/" in model_id  # NVIDIA models have / in ID

    def _initialize_model_registry(self) -> Dict[str, ModelInfo]:
        """Initialize model registry with NVIDIA + Ollama models - optimized from benchmark tests"""
        models = {}

        # === TIER 1: FASTEST HIGH-QUALITY (Use these by default) ===
        # Best overall - Llama 4 Maverick (0.56s, 10/10 quality)
        models["meta/llama-4-maverick-17b-128e-instruct"] = ModelInfo(
            id="meta/llama-4-maverick-17b-128e-instruct",
            name="Llama 4 Maverick",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=128000,
            specialty=[TaskType.GENERAL, TaskType.CREATIVE, TaskType.ANALYSIS],
            speed_score=10,
            quality_score=10,
            cost_tier="free",
        )

        # Best reasoning - DeepSeek V4 Flash (available, excellent reasoning)
        models["deepseek-ai/deepseek-v4-flash"] = ModelInfo(
            id="deepseek-ai/deepseek-v4-flash",
            name="DeepSeek V4 Flash",
            provider="nvidia",
            tier="reasoning",
            category="reasoning",
            context_length=128000,
            specialty=[TaskType.REASONING, TaskType.MATH],
            speed_score=9,
            quality_score=9,
            cost_tier="free",
        )

        # Fast multimodal - Phi-4 Mini (available, fast general-purpose)
        models["microsoft/phi-4-mini-instruct"] = ModelInfo(
            id="microsoft/phi-4-mini-instruct",
            name="Phi-4 Mini",
            provider="nvidia",
            tier="fast",
            category="general",
            context_length=128000,
            specialty=[TaskType.GENERAL, TaskType.CODE],
            speed_score=10,
            quality_score=8,
            cost_tier="free",
        )

        # === TIER 2: HIGH QUALITY (Fallbacks) ===
        # Llama 3.1 70B (0.75s, 10/10 quality)
        models["meta/llama-3.1-70b-instruct"] = ModelInfo(
            id="meta/llama-3.1-70b-instruct",
            name="Llama 3.1 70B",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=128000,
            specialty=[TaskType.GENERAL, TaskType.ANALYSIS, TaskType.CREATIVE],
            speed_score=7,
            quality_score=10,
            cost_tier="free",
        )

        # Qwen 3 Next 80B (0.70s, 10/10 quality)
        models["qwen/qwen3-next-80b-a3b-instruct"] = ModelInfo(
            id="qwen/qwen3-next-80b-a3b-instruct",
            name="Qwen 3 Next 80B",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=32000,
            specialty=[TaskType.GENERAL, TaskType.CODE],
            speed_score=8,
            quality_score=10,
            cost_tier="free",
        )

        # === TIER 3: FAST BUT LESS CAPABLE (For speed-critical tasks) ===
        # Fast small - Gemma 3 4B (0.48s, 7/10 quality)
        models["google/gemma-3-4b-it"] = ModelInfo(
            id="google/gemma-3-4b-it",
            name="Gemma 3 4B",
            provider="nvidia",
            tier="fast",
            category="general",
            context_length=4096,
            specialty=[TaskType.GENERAL],
            speed_score=10,
            quality_score=7,
            cost_tier="free",
        )

        # Llama 3.1 8B (0.52s, 9/10 quality)
        models["meta/llama-3.1-8b-instruct"] = ModelInfo(
            id="meta/llama-3.1-8b-instruct",
            name="Llama 3.1 8B",
            provider="nvidia",
            tier="fast",
            category="general",
            context_length=8192,
            specialty=[TaskType.GENERAL],
            speed_score=10,
            quality_score=9,
            cost_tier="free",
        )

        # === SPECIALTY MODELS ===
        # Most capable coder - Qwen Coder 480B (slower but most capable)
        models["qwen/qwen3-coder-480b-a35b-instruct"] = ModelInfo(
            id="qwen/qwen3-coder-480b-a35b-instruct",
            name="Qwen Coder 480B",
            provider="nvidia",
            tier="coding",
            category="coding",
            context_length=32000,
            specialty=[TaskType.CODE],
            speed_score=6,
            quality_score=10,
            cost_tier="free",
        )

        # NOTE: Llama 3.1 405B not provisioned; using 70B as flagship general
        # Llama 3.1 70B available at meta/llama-3.1-70b-instruct (already below)

        # Large reasoning - Mistral Large 3 675B (available)
        models["mistralai/mistral-large-3-675b-instruct-2512"] = ModelInfo(
            id="mistralai/mistral-large-3-675b-instruct-2512",
            name="Mistral Large 3",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=32000,
            specialty=[TaskType.GENERAL, TaskType.REASONING, TaskType.ANALYSIS],
            speed_score=6,
            quality_score=10,
            cost_tier="free",
        )

        # Google's best - Gemma 4 31B (available)
        models["google/gemma-4-31b-it"] = ModelInfo(
            id="google/gemma-4-31b-it",
            name="Gemma 4 31B",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=32000,
            specialty=[TaskType.GENERAL, TaskType.ANALYSIS],
            speed_score=7,
            quality_score=9,
            cost_tier="free",
        )

        # NVIDIA optimized - Nemotron Super 49B (available)
        models["nvidia/llama-3.3-nemotron-super-49b-v1.5"] = ModelInfo(
            id="nvidia/llama-3.3-nemotron-super-49b-v1.5",
            name="Nemotron Super 49B",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=128000,
            specialty=[TaskType.GENERAL, TaskType.ANALYSIS],
            speed_score=7,
            quality_score=10,
            cost_tier="free",
        )

        # Ollama Local Models (must match actual running Ollama instance)
        models["qwen2.5-coder:3b-instruct-q4_K_M"] = ModelInfo(
            id="qwen2.5-coder:3b-instruct-q4_K_M",
            name="Qwen 2.5 Coder 3B Q4 (Local)",
            provider="ollama",
            tier="local",
            category="coding",
            context_length=8192,
            specialty=[TaskType.CODE, TaskType.GENERAL],
            speed_score=10,
            quality_score=7,
            cost_tier="free",
        )

        models["qwen2.5-coder:3b"] = ModelInfo(
            id="qwen2.5-coder:3b",
            name="Qwen 2.5 Coder 3B (Local)",
            provider="ollama",
            tier="local",
            category="coding",
            context_length=8192,
            specialty=[TaskType.CODE, TaskType.GENERAL],
            speed_score=10,
            quality_score=6,
            cost_tier="free",
        )

        models["qwen2.5-coder:7b"] = ModelInfo(
            id="qwen2.5-coder:7b",
            name="Qwen 2.5 Coder 7B (Local)",
            provider="ollama",
            tier="local",
            category="coding",
            context_length=8192,
            specialty=[TaskType.CODE, TaskType.GENERAL],
            speed_score=9,
            quality_score=7,
            cost_tier="free",
        )

        return models

    async def detect_available_models(
        self, force_refresh: bool = False
    ) -> Dict[str, List[str]]:
        """
        Detect available models from Ollama and NVIDIA API.

        Returns:
            {
                "ollama": ["llama3:latest", "codellama:7b", ...],
                "nvidia": ["meta/llama-4-maverick-17b-128e-instruct", ...],
                "all": [... all available model IDs ...]
            }
        """
        # Check cache validity
        if not force_refresh and self._last_detection:
            if datetime.utcnow() - self._last_detection < self._detection_cache_ttl:
                return {
                    "ollama": self._available_ollama_models,
                    "nvidia": self._available_nvidia_models,
                    "all": self._available_ollama_models
                    + self._available_nvidia_models,
                }

        ollama_models = []
        nvidia_models = []

        # Detect Ollama models
        ollama_models = await self._detect_ollama_models()

        # Detect NVIDIA models (if API keys available)
        if nvidia_key_pool.available:
            nvidia_models = await self._detect_nvidia_models()

        # Update cache
        self._available_ollama_models = ollama_models
        self._available_nvidia_models = nvidia_models
        self._last_detection = datetime.utcnow()

        logger.info(
            f"Model detection: {len(ollama_models)} Ollama, {len(nvidia_models)} NVIDIA"
        )

        return {
            "ollama": ollama_models,
            "nvidia": nvidia_models,
            "all": ollama_models + nvidia_models,
        }

    async def _detect_ollama_models(self) -> List[str]:
        """Query local Ollama for available models"""
        models = []

        # Try primary URL
        ollama_urls = [settings.OLLAMA_BASE_URL]
        if settings.OLLAMA_GPU_URL:
            ollama_urls.append(settings.OLLAMA_GPU_URL)

        for url in ollama_urls:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{url}/api/tags", timeout=3.0)
                    if response.status_code == 200:
                        data = response.json()
                        models = [
                            m.get("name", "")
                            for m in data.get("models", [])
                            if m.get("name")
                        ]
                        logger.info(f"Ollama at {url}: {len(models)} models")
                        break
            except Exception as e:
                logger.debug(f"Ollama not available at {url}: {e}")
                continue

        return models

    async def _detect_nvidia_models(self) -> List[str]:
        """Query NVIDIA API for available models using key pool"""
        models = []

        key = nvidia_key_pool.get()
        if not key:
            logger.debug("No NVIDIA API key available from pool")
            return models

        nvidia_url = "https://integrate.api.nvidia.com/v1"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{nvidia_url}/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=5.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    # Extract model IDs from the response
                    for model in data.get("data", []):
                        model_id = model.get("id", "")
                        if model_id:
                            models.append(model_id)
                    logger.info(f"NVIDIA API: {len(models)} models available")
                    nvidia_key_pool.report_success(key)
                elif response.status_code in (401, 429):
                    cooldown = 60.0 if response.status_code == 429 else 10.0
                    nvidia_key_pool.report_error(key, cooldown=cooldown)
                    logger.warning(
                        f"NVIDIA API key error {response.status_code}, cooling {cooldown}s"
                    )
                else:
                    nvidia_key_pool.report_error(key, cooldown=10.0)
                    logger.warning(f"NVIDIA API error {response.status_code}")
        except Exception as e:
            logger.debug(f"NVIDIA API error: {e}")
            nvidia_key_pool.report_error(key, cooldown=30.0)

        return models

    def get_available_models_sync(self) -> Dict[str, List[str]]:
        """
        Synchronous version - returns cached available models.
        Returns empty dict if detection hasn't run yet.
        """
        if not self._last_detection:
            return {"ollama": [], "nvidia": [], "all": []}

        return {
            "ollama": self._available_ollama_models,
            "nvidia": self._available_nvidia_models,
            "all": self._available_ollama_models + self._available_nvidia_models,
        }

    def is_model_available(self, model_id: str) -> bool:
        """Check if a specific model is currently available"""
        available = self.get_available_models_sync()
        return model_id in available["all"]

    def analyze_task(self, prompt: str, context_length: int = 0) -> TaskType:
        """Analyze task to determine best model type"""
        prompt_lower = prompt.lower()

        # Code detection
        code_patterns = [
            r"\bfunction\b",
            r"\bclass\b",
            r"\bdef\b",
            r"\bimport\b",
            r"\breturn\b",
            r"\bvar\b",
            r"\bconst\b",
            r"\blet\b",
            r"```",
            r"\bcode\b",
            r"\bprogramming\b",
            r"\balgorithm\b",
            r"\bbug\b",
            r"\bdebug\b",
            r"\bAPI\b",
            r"\bpython\b",
            r"\bjavascript\b",
            r"\btypescript\b",
            r"\brust\b",
            r"\bgo\b",
        ]

        if any(re.search(p, prompt_lower) for p in code_patterns):
            return TaskType.CODE

        # Math detection
        math_patterns = [
            r"\bmath\b",
            r"\bcalculate\b",
            r"\bequation\b",
            r"\bformula\b",
            r"\bsolve\b",
            r"\bprove\b",
            r"\btheorem\b",
            r"\bderivative\b",
            r"\bintegral\b",
            r"\b algebra\b",
            r"\bgeometry\b",
            r"\d+\s*[\+\-\*\/]\s*\d+",
        ]

        if any(re.search(p, prompt_lower) for p in math_patterns):
            return TaskType.MATH

        # Reasoning detection
        reasoning_patterns = [
            r"\breason\b",
            r"\banalyze\b",
            r"\bthink\b",
            r"\bexplain\b",
            r"\bwhy\b",
            r"\bhow\b",
            r"\bcompare\b",
            r"\bcontrast\b",
            r"\bevaluate\b",
            r"\bassess\b",
            r"\bargue\b",
            r"\bdebate\b",
            r"\blogic\b",
            r"\binference\b",
            r"\bdeduce\b",
        ]

        if any(re.search(p, prompt_lower) for p in reasoning_patterns):
            return TaskType.REASONING

        # Creative detection
        creative_patterns = [
            r"\bwrite\b",
            r"\bstory\b",
            r"\bpoem\b",
            r"\bsong\b",
            r"\bcreative\b",
            r"\bimagine\b",
            r"\bfiction\b",
            r"\bnarrative\b",
            r"\bhaiku\b",
            r"\bverse\b",
            r"\btale\b",
        ]

        if any(re.search(p, prompt_lower) for p in creative_patterns):
            return TaskType.CREATIVE

        # Long context detection
        if context_length > 32000 or len(prompt) > 5000:
            return TaskType.LONG_CONTEXT

        # Multilingual detection
        multilingual_patterns = [
            r"\btranslate\b",
            r"\blanguage\b",
            r"\bmultilingual\b",
            r"\bespañol\b",
            r"\bfrançais\b",
            r"\b中文\b",
            r"\b日本語\b",
            r"\bdeutsch\b",
            r"\bportuguês\b",
        ]

        if any(re.search(p, prompt_lower) for p in multilingual_patterns):
            return TaskType.MULTILINGUAL

        return TaskType.GENERAL

    def select_model(
        self,
        prompt: str,
        preferred_model: Optional[str] = None,
        max_context: int = 128000,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        require_local: bool = False,
        fallback_chain: bool = True,
    ) -> Tuple[str, ModelInfo]:
        """
        Select the best model for a task

        Returns: (model_id, model_info)
        """

        # 1. If user explicitly requested a model, use it (if available in registry)
        if preferred_model and preferred_model in self.models:
            logger.info(f"Using user-specified model: {preferred_model}")
            return preferred_model, self.models[preferred_model]

        # 2. Analyze task type
        task_type = self.analyze_task(prompt, max_context)
        logger.info(f"Detected task type: {task_type.value}")

        # 3. Get available models (cached)
        available = self.get_available_models_sync()
        available_set = set(available["all"])

        # 4. Filter models by requirements + availability
        candidates = []
        for model_id, model in self.models.items():
            # Skip if requires local but model is cloud
            if require_local and model.provider != "ollama":
                continue

            # Skip if context too small
            if model.context_length < max_context:
                continue

            # Skip if model is not in available set (auto-detection)
            # But allow if no detection has run yet (backwards compatibility)
            if available["all"] and model_id not in available_set:
                continue

            # Score the model
            score = 0

            # Specialty match bonus
            if task_type in model.specialty:
                score += 50

            # Speed bonus
            if prefer_speed:
                score += model.speed_score * 5

            # Quality bonus
            if prefer_quality:
                score += model.quality_score * 5

            # Local preference (faster)
            if model.provider == "ollama":
                score += 30

            candidates.append((model_id, model, score))

        # 4. Sort by score
        candidates.sort(key=lambda x: x[2], reverse=True)

        if not candidates:
            # Fallback to local Ollama qwen2.5-coder:3b
            if "qwen2.5-coder:3b" in self.models:
                return "qwen2.5-coder:3b", self.models["qwen2.5-coder:3b"]
            # Ultimate fallback to first registered ollama model
            for mid, m in self.models.items():
                if m.provider == "ollama":
                    return mid, m
            return "qwen2.5-coder:3b-instruct-q4_K_M", self.models[
                "qwen2.5-coder:3b-instruct-q4_K_M"
            ]

        # 5. Return best model
        best_model_id, best_model, score = candidates[0]
        logger.info(f"Selected model: {best_model_id} (score: {score})")

        return best_model_id, best_model

    def get_fallback_chain(self, primary_model: str) -> List[str]:
        """
        Generate optimized fallback chain based on benchmark results.
        Filters to only include available models.

        Example: Llama 4 Maverick → Llama 3.1 70B → Phi-3 Mini
        """
        if primary_model not in self.models:
            return ["google/gemma-3-4b-it"]

        model = self.models[primary_model]
        chain = [primary_model]

        # Get available models
        available = self.get_available_models_sync()
        available_set = set(available["all"])
        has_detected = bool(available["all"])

        # Code-specific chain (fastest coders first)
        if TaskType.CODE in model.specialty:
            chain.extend(
                [
                    "qwen/qwen3-coder-480b-a35b-instruct",  # Most capable coder
                    "qwen/qwen3-next-80b-a3b-instruct",  # Fast coder
                    "google/gemma-3-4b-it",  # Fastest fallback
                ]
            )
        # Reasoning-specific chain
        elif TaskType.REASONING in model.specialty or TaskType.MATH in model.specialty:
            chain.extend(
                [
                    "deepseek-ai/deepseek-v4-flash",  # Best reasoning
                    "meta/llama-3.1-70b-instruct",  # High quality general
                    "google/gemma-3-4b-it",  # Fastest fallback
                ]
            )
        # General-purpose chain (speed + quality optimized)
        else:
            chain.extend(
                [
                    "meta/llama-4-maverick-17b-128e-instruct",  # Best quality/speed
                    "meta/llama-3.1-70b-instruct",  # High quality fallback
                    "google/gemma-3-4b-it",  # Fastest fallback
                ]
            )

        # Remove duplicates
        seen = set()
        unique_chain = []
        for model_id in chain:
            if model_id not in seen:
                seen.add(model_id)
                unique_chain.append(model_id)

        # Filter by available models if detection has run
        if has_detected:
            filtered_chain = [m for m in unique_chain if m in available_set]
            # If no models available in chain, try any available model
            if not filtered_chain:
                filtered_chain = list(available_set)
            return filtered_chain if filtered_chain else unique_chain

        return unique_chain

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count"""
        # Approximate: 1 token ≈ 4 characters for English
        return len(text) // 4

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get model information"""
        return self.models.get(model_id)

    def list_models_by_specialty(self, task_type: TaskType) -> List[ModelInfo]:
        """List all models suited for a task type"""
        return [model for model in self.models.values() if task_type in model.specialty]

    def update_benchmark(self, model_id: str, benchmark_data: Dict):
        """Update model benchmark data"""
        if model_id not in self.benchmarks:
            self.benchmarks[model_id] = {}
        self.benchmarks[model_id].update(benchmark_data)

    def get_recommended_models(
        self, task_type: Optional[TaskType] = None, limit: int = 5
    ) -> List[ModelInfo]:
        """Get recommended models, optionally filtered by task type"""
        if task_type:
            models = self.list_models_by_specialty(task_type)
        else:
            models = list(self.models.values())

        # Sort by quality score, then speed
        models.sort(key=lambda m: (m.quality_score, m.speed_score), reverse=True)

        return models[:limit]


def get_optimal_model_for_task(self, task_type: TaskType) -> str:
    """
    Get the best model for a specific task type based on benchmark results.

    Returns model ID string.
    """
    if task_type == TaskType.CODE:
        return "qwen/qwen3-coder-480b-a35b-instruct"  # Best coder
    elif task_type == TaskType.REASONING or task_type == TaskType.MATH:
        return "deepseek-ai/deepseek-v4-flash"  # Best reasoning
    elif task_type == TaskType.MULTILINGUAL:
        return "mistralai/mistral-large-3-675b-instruct-2512"  # Multilingual
    elif task_type == TaskType.LONG_CONTEXT:
        return "meta/llama-3.1-70b-instruct"  # Large context available
    elif task_type == TaskType.CREATIVE:
        return "meta/llama-4-maverick-17b-128e-instruct"  # Best creative
    else:
        # Default to Llama 4 Maverick - best overall quality/speed balance
        return "meta/llama-4-maverick-17b-128e-instruct"
