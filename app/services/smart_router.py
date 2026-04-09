"""
Smart Model Router for OneQueue
Intelligently selects the best model based on task requirements
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

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

        # Best coder - Qwen Coder 32B (0.63s, 10/10 code quality)
        models["qwen/qwen2.5-coder-32b-instruct"] = ModelInfo(
            id="qwen/qwen2.5-coder-32b-instruct",
            name="Qwen Coder 32B",
            provider="nvidia",
            tier="coding",
            category="coding",
            context_length=32000,
            specialty=[TaskType.CODE],
            speed_score=9,
            quality_score=10,
            cost_tier="free",
        )

        # Best reasoning - DeepSeek R1 Distill (0.73s, 10/10 reasoning)
        models["deepseek-ai/deepseek-r1-distill-llama-8b"] = ModelInfo(
            id="deepseek-ai/deepseek-r1-distill-llama-8b",
            name="DeepSeek R1 Distill",
            provider="nvidia",
            tier="reasoning",
            category="reasoning",
            context_length=128000,
            specialty=[TaskType.REASONING, TaskType.MATH],
            speed_score=8,
            quality_score=10,
            cost_tier="free",
        )

        # Best vision + general - Phi-3.5 Vision (0.52s, 9/10 quality)
        models["microsoft/phi-3.5-vision-instruct"] = ModelInfo(
            id="microsoft/phi-3.5-vision-instruct",
            name="Phi-3.5 Vision",
            provider="nvidia",
            tier="multimodal",
            category="general",
            context_length=128000,
            specialty=[TaskType.GENERAL, TaskType.CODE, TaskType.MULTILINGUAL],
            speed_score=10,
            quality_score=9,
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
        # Fastest overall - Phi-3 Mini (0.52s, 8/10 quality)
        models["microsoft/phi-3-mini-4k-instruct"] = ModelInfo(
            id="microsoft/phi-3-mini-4k-instruct",
            name="Phi-3 Mini",
            provider="nvidia",
            tier="fast",
            category="general",
            context_length=4096,
            specialty=[TaskType.GENERAL],
            speed_score=10,
            quality_score=8,
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

        # Highest quality - Llama 3.1 405B (0.76s, 10/10 quality, 405B params!)
        models["meta/llama-3.1-405b-instruct"] = ModelInfo(
            id="meta/llama-3.1-405b-instruct",
            name="Llama 3.1 405B",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=128000,
            specialty=[TaskType.LONG_CONTEXT, TaskType.ANALYSIS, TaskType.CREATIVE],
            speed_score=5,
            quality_score=10,
            cost_tier="free",
        )

        # Multilingual - Mistral 7B (0.69s, 9/10 quality)
        models["mistralai/mistral-7b-instruct"] = ModelInfo(
            id="mistralai/mistral-7b-instruct",
            name="Mistral 7B Instruct",
            provider="nvidia",
            tier="fast",
            category="general",
            context_length=32000,
            specialty=[TaskType.GENERAL, TaskType.MULTILINGUAL, TaskType.CREATIVE],
            speed_score=9,
            quality_score=9,
            cost_tier="free",
        )

        # Google's best - Gemma 3 27B (0.86s, 9/10 quality)
        models["google/gemma-3-27b-it"] = ModelInfo(
            id="google/gemma-3-27b-it",
            name="Gemma 3 27B",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=32000,
            specialty=[TaskType.GENERAL, TaskType.ANALYSIS],
            speed_score=7,
            quality_score=9,
            cost_tier="free",
        )

        # NVIDIA optimized - Nemotron Ultra (0.69s, 10/10 quality)
        models["nvidia/llama-3.1-nemotron-ultra"] = ModelInfo(
            id="nvidia/llama-3.1-nemotron-ultra",
            name="Nemotron Ultra",
            provider="nvidia",
            tier="flagship",
            category="general",
            context_length=128000,
            specialty=[TaskType.GENERAL, TaskType.ANALYSIS],
            speed_score=8,
            quality_score=10,
            cost_tier="free",
        )

        # Ollama Local Models
        models["llama3:latest"] = ModelInfo(
            id="llama3:latest",
            name="Llama 3 (Local)",
            provider="ollama",
            tier="local",
            category="general",
            context_length=8192,
            specialty=[TaskType.GENERAL],
            speed_score=10,
            quality_score=7,
            cost_tier="free",
        )

        models["llama3:8b-instruct-q4_K_M"] = ModelInfo(
            id="llama3:8b-instruct-q4_K_M",
            name="Llama 3 8B Q4 (Local)",
            provider="ollama",
            tier="local",
            category="general",
            context_length=8192,
            specialty=[TaskType.GENERAL],
            speed_score=10,
            quality_score=6,
            cost_tier="free",
        )

        return models

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

        # 1. If user explicitly requested a model, use it (if available)
        if preferred_model and preferred_model in self.models:
            logger.info(f"Using user-specified model: {preferred_model}")
            return preferred_model, self.models[preferred_model]

        # 2. Analyze task type
        task_type = self.analyze_task(prompt, max_context)
        logger.info(f"Detected task type: {task_type.value}")

        # 3. Filter models by requirements
        candidates = []
        for model_id, model in self.models.items():
            # Skip if requires local but model is cloud
            if require_local and model.provider != "ollama":
                continue

            # Skip if context too small
            if model.context_length < max_context:
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
            # Fallback to Llama 3 local
            return "llama3:latest", self.models["llama3:latest"]

        # 5. Return best model
        best_model_id, best_model, score = candidates[0]
        logger.info(f"Selected model: {best_model_id} (score: {score})")

        return best_model_id, best_model

    def get_fallback_chain(self, primary_model: str) -> List[str]:
        """
        Generate optimized fallback chain based on benchmark results

        Example: Llama 4 Maverick → Llama 3.1 70B → Phi-3 Mini
        """
        if primary_model not in self.models:
            return ["microsoft/phi-3-mini-4k-instruct"]

        model = self.models[primary_model]
        chain = [primary_model]

        # Code-specific chain (fastest coders first)
        if TaskType.CODE in model.specialty:
            chain.extend(
                [
                    "qwen/qwen2.5-coder-32b-instruct",  # Fast + capable coder
                    "qwen/qwen3-coder-480b-a35b-instruct",  # Most capable coder
                    "microsoft/phi-3-mini-4k-instruct",  # Fastest fallback
                ]
            )
        # Reasoning-specific chain
        elif TaskType.REASONING in model.specialty or TaskType.MATH in model.specialty:
            chain.extend(
                [
                    "deepseek-ai/deepseek-r1-distill-llama-8b",  # Best reasoning
                    "meta/llama-3.1-70b-instruct",  # High quality general
                    "microsoft/phi-3-mini-4k-instruct",  # Fastest fallback
                ]
            )
        # General-purpose chain (speed + quality optimized)
        else:
            chain.extend(
                [
                    "meta/llama-4-maverick-17b-128e-instruct",  # Best quality/speed
                    "meta/llama-3.1-70b-instruct",  # High quality fallback
                    "microsoft/phi-3-mini-4k-instruct",  # Fastest fallback
                ]
            )

        # Remove duplicates
        seen = set()
        unique_chain = []
        for model_id in chain:
            if model_id not in seen:
                seen.add(model_id)
                unique_chain.append(model_id)

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
        self, task_type: TaskType = None, limit: int = 5
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
            return "qwen/qwen2.5-coder-32b-instruct"  # Best coder (0.63s)
        elif task_type == TaskType.REASONING or task_type == TaskType.MATH:
            return "deepseek-ai/deepseek-r1-distill-llama-8b"  # Best reasoning (0.73s)
        elif task_type == TaskType.MULTILINGUAL:
            return "mistralai/mistral-7b-instruct"  # Great multilingual support
        elif task_type == TaskType.LONG_CONTEXT:
            return "meta/llama-3.1-405b-instruct"  # Highest quality, large context
        elif task_type == TaskType.CREATIVE:
            return "meta/llama-4-maverick-17b-128e-instruct"  # Best creative
        else:
            # Default to Llama 4 Maverick - best overall quality/speed balance
            return "meta/llama-4-maverick-17b-128e-instruct"
