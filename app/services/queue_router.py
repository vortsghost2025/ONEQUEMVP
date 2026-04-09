"""
OneQueue Routing Rule - Updated Worker Integration
Replaces phi-3-mini with benchmark-optimized models
"""

import logging
from typing import Optional
from app.services.router_function import get_router_function, route_task
from app.services.smart_router import SmartRouter, TaskType

logger = logging.getLogger("onequeue.queue_router")


class QueueRouter:
    """
    OneQueue routing rule that integrates with the worker.

    Routing Strategy (from benchmark sweep 2026-04-09):
    - Default: meta/llama-4-maverick-17b-128e-instruct (0.56s, 10/10 quality)
    - Code: qwen/qwen2.5-coder-32b-instruct (0.63s, 10/10 code quality)
    - Reasoning/Math: deepseek-ai/deepseek-r1-distill-llama-8b (0.73s, 10/10 reasoning)
    - Fallback: microsoft/phi-3-mini-4k-instruct (0.52s, 8/10 quality)

    This replaces the previous default of microsoft/phi-3-mini-4k-instruct.
    """

    def __init__(self):
        self.router_function = get_router_function()
        self.smart_router = SmartRouter()

        logger.info("QueueRouter initialized with benchmark-optimized models")

    def select_model_for_task(
        self,
        prompt: str,
        preferred_model: Optional[str] = None,
        prefer_speed: bool = False,
        prefer_quality: bool = True,
    ) -> str:
        """
        Select best model for a task using updated routing rules.

        Args:
            prompt: Task prompt (used for task type detection)
            preferred_model: User-specified model (overrides routing)
            prefer_speed: Optimize for speed over quality
            prefer_quality: Optimize for quality (default)

        Returns:
            Model ID string (e.g., "meta/llama-4-maverick-17b-128e-instruct")
        """
        # If user specified a model, use it
        if preferred_model:
            logger.info(f"Using user-specified model: {preferred_model}")
            return preferred_model

        # Detect task type
        task_type_enum = self.smart_router.analyze_task(prompt)
        task_type_str = task_type_enum.value

        logger.info(f"Detected task type: {task_type_str}")

        # Use router function for model selection
        model_id, fallback_chain = self.router_function.select_model(
            task_type=task_type_str,
            prefer_speed=prefer_speed,
            prefer_quality=prefer_quality,
        )

        logger.info(f"Selected model: {model_id} | Fallback: {fallback_chain[:3]}")

        return model_id

    def get_fallback_chain(self, model_id: str) -> list:
        """Get fallback chain for a model"""
        return self.smart_router.get_fallback_chain(model_id)

    def is_nvidia_model(self, model_id: str) -> bool:
        """Check if model uses NVIDIA API"""
        return self.smart_router._is_nvidia_model(model_id)


# Singleton
_queue_router: Optional[QueueRouter] = None


def get_queue_router() -> QueueRouter:
    """Get or create queue router singleton"""
    global _queue_router
    if _queue_router is None:
        _queue_router = QueueRouter()
    return _queue_router


# Convenience function for worker integration
def route_queue_task(prompt: str, preferred_model: Optional[str] = None) -> str:
    """
    Quick routing for queue tasks.

    Usage in worker:
        from app.services.queue_router import route_queue_task

        model_id = route_queue_task(task.prompt, task.model)
        if model_id.startswith("nvidia:") or "/" in model_id:
            # Use NVIDIA API
        else:
            # Use Ollama
    """
    router = get_queue_router()
    return router.select_model_for_task(prompt, preferred_model)
