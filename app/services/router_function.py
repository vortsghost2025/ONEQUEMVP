"""
OneQueue Router Function - Fast Model Selection
Optimized for RTX 5060 + NVIDIA API
Uses benchmark-validated models from 2026-04-09
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("onequeue.router_function")


class RouterFunction:
    """
    Fast router function using pre-computed routing rules.
    Loads router.json and provides O(1) model selection.
    """

    def __init__(self, config_path: str = "router.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.routing_rules = self.config.get("routing_rules", {})
        self.default_model = self.config.get("default_model")

        logger.info(f"RouterFunction loaded: {len(self.routing_rules)} task types")

    def _load_config(self) -> Dict:
        """Load router configuration from JSON"""
        if not self.config_path.exists():
            logger.warning(f"Config not found: {self.config_path}, using defaults")
            return self._get_default_config()

        with open(self.config_path, "r") as f:
            return json.load(f)

    def _get_default_config(self) -> Dict:
        """Fallback default configuration"""
        return {
            "default_model": "meta/llama-4-maverick-17b-128e-instruct",
            "routing_rules": {
                "general": {
                    "primary": "meta/llama-4-maverick-17b-128e-instruct",
                    "fallback_chain": [
                        "meta/llama-4-maverick-17b-128e-instruct",
                        "microsoft/phi-3-mini-4k-instruct",
                    ],
                }
            },
        }

    def select_model(
        self,
        task_type: str,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        max_latency_ms: Optional[int] = None,
    ) -> Tuple[str, List[str]]:
        """
        Select best model for a task type.

        Args:
            task_type: One of 'code', 'reasoning', 'math', 'creative', 'general', 'analysis', 'long_context', 'multilingual'
            prefer_speed: If True, prefer faster models (tier 3)
            prefer_quality: If True, prefer higher quality models (tier 1/2)
            max_latency_ms: Maximum acceptable latency in milliseconds

        Returns:
            (primary_model, fallback_chain)
        """
        # Normalize task type
        task_type = task_type.lower().strip()

        # Get routing rule
        rule = self.routing_rules.get(task_type)

        if not rule:
            logger.info(f"Unknown task type '{task_type}', using default")
            return self.default_model, [self.default_model]

        primary = rule["primary"]
        fallback_chain = rule["fallback_chain"]

        # Apply speed/quality preferences
        if prefer_speed:
            # Use fastest tier 3 models
            tier_3 = self.config.get("tier_rankings", {}).get(
                "tier_3_fast_but_limited", []
            )
            if tier_3:
                primary = tier_3[0]
                fallback_chain = tier_3

        elif prefer_quality:
            # Use tier 1 flagship models
            tier_1 = self.config.get("tier_rankings", {}).get(
                "tier_1_fastest_high_quality", []
            )
            if tier_1:
                primary = tier_1[0]
                fallback_chain = tier_1

        # Apply latency constraint
        if max_latency_ms:
            benchmark_data = self.config.get("benchmark_results", {})
            for model_id in fallback_chain:
                model_bench = benchmark_data.get(model_id, {})
                if model_bench.get("avg_latency_ms", 9999) <= max_latency_ms:
                    primary = model_id
                    break

        logger.info(f"Selected model for {task_type}: {primary}")
        return primary, fallback_chain

    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get benchmark data for a model"""
        return self.config.get("benchmark_results", {}).get(model_id)

    def get_all_models(self) -> List[str]:
        """Get all available models"""
        models = set()
        for rule in self.routing_rules.values():
            models.add(rule["primary"])
            models.update(rule["fallback_chain"])
        return sorted(list(models))

    def get_fastest_models(self, limit: int = 5) -> List[str]:
        """Get fastest models by latency"""
        benchmark_data = self.config.get("benchmark_results", {})
        sorted_models = sorted(
            benchmark_data.items(), key=lambda x: x[1].get("avg_latency_ms", 9999)
        )
        return [m[0] for m in sorted_models[:limit]]

    def get_best_quality_models(self, limit: int = 5) -> List[str]:
        """Get highest quality models"""
        benchmark_data = self.config.get("benchmark_results", {})
        sorted_models = sorted(
            benchmark_data.items(),
            key=lambda x: (
                -x[1].get("quality_score", 0),
                x[1].get("avg_latency_ms", 9999),
            ),
        )
        return [m[0] for m in sorted_models[:limit]]

    def reload_config(self):
        """Reload configuration from disk"""
        self.config = self._load_config()
        self.routing_rules = self.config.get("routing_rules", {})
        self.default_model = self.config.get("default_model")
        logger.info("Router config reloaded")


# Singleton instance
_router_function: Optional[RouterFunction] = None


def get_router_function() -> RouterFunction:
    """Get or create router function singleton"""
    global _router_function
    if _router_function is None:
        _router_function = RouterFunction()
    return _router_function


# Convenience function for quick routing
def route_task(
    task_type: str,
    prefer_speed: bool = False,
    prefer_quality: bool = False,
) -> str:
    """
    Quick routing function - returns best model ID.

    Usage:
        model_id = route_task("code")
        model_id = route_task("reasoning", prefer_quality=True)
    """
    router = get_router_function()
    primary, _ = router.select_model(
        task_type=task_type,
        prefer_speed=prefer_speed,
        prefer_quality=prefer_quality,
    )
    return primary
