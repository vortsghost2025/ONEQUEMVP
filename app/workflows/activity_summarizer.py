"""WE4FREE Activity Summarizer - OneQueue Workflow

Ingests agent completion reports, commit batches, runtime snapshots,
and lane review notes. Produces structured summaries for WE4FREE Pulse.

Uses local Ollama by default. Falls back to NVIDIA cloud API if needed.
"""

import json
import uuid
import logging
import time
import httpx
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

from app.config import settings
from app.services.smart_router import SmartRouter

logger = logging.getLogger("onequeue.we4free")


# --- Value types ---


class ActivityCategory:
    SECURITY = "security"
    REPAIR = "repair"
    FEATURE = "feature"
    HOUSEKEEPING = "housekeeping"
    VISIBILITY = "visibility"
    AUTONOMY = "autonomy"


class Relevance:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SuggestedSurface:
    PULSE = "Pulse"
    CATCHUP = "CatchUp"
    NONE = "None"


# --- Schemas ---


@dataclass
class ActivityInput:
    """A single activity packet to summarize."""

    kind: str  # commit_batch | agent_report | runtime_snapshot | lane_note
    title: str
    body: str
    source: str  # e.g. "repo:ONEQUEMVP" or "lane:exterior-synthesis"
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ActivitySummary:
    """Structured output from the summarizer."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: str = ActivityCategory.HOUSEKEEPING
    repo_or_lane: str = ""
    summary: str = ""
    operator_relevance: str = Relevance.LOW
    needs_sean: bool = False
    suggested_surface: str = SuggestedSurface.NONE
    model_used: str = ""
    processing_time_ms: int = 0
    timestamp: str = ""
    raw_input_kind: str = ""
    confidence: float = 0.0


# --- Prompt ---

PROMPT_TEMPLATE = """\
You are the WE4FREE Activity Summarizer for Sean's autonomous agent ecosystem.

Categorize each activity packet and produce structured JSON output.

CATEGORIES:
- security: vulnerability, exploit, unauthorized access, credential leak
- repair: bugfix, rollback, hotfix, regression, broken pipeline
- feature: new capability, enhancement, API addition, integration
- housekeeping: cleanup, refactor, dependency update, config change
- visibility: status report, progress update, dashboard metric
- autonomy: agent decision, self-healing, adaptive behavior

RELEVANCE: high (act now), medium (24h), low (informational)
SURFACE: Pulse (high/cross-cutting), CatchUp (medium/batchable), None (low/auto)

Input Kind: {kind}
Source: {source}
Title: {title}
Body: {body}

Return ONLY valid JSON with this exact schema:
{{"category": "...", "summary": "...", "operator_relevance": "...", "needs_sean": ..., "suggested_surface": "..."}}
"""


# --- Core workflow ---


class ActivitySummarizer:
    """WE4FREE Activity Summarizer — local Ollama first, NVIDIA fallback."""

    def __init__(self):
        self.router = SmartRouter()
        self.local_model = "qwen2.5-coder:3b-instruct-q4_K_M"

    def _build_prompt(self, packet: ActivityInput) -> str:
        body = packet.body[:6000]
        return PROMPT_TEMPLATE.format(
            kind=packet.kind,
            source=packet.source,
            title=packet.title,
            body=body,
        )

    async def process(self, packet: ActivityInput) -> ActivitySummary:
        prompt = self._build_prompt(packet)
        start_ms = int(time.time() * 1000)

        model_id, _ = self.router.select_model(prompt=prompt, require_local=True)
        result = ActivitySummary(
            raw_input_kind=packet.kind,
            repo_or_lane=packet.source,
        )

        # --- Try local Ollama ---
        try:
            resp = httpx.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 512},
                },
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "").strip()
                model_used = data.get("model", model_id)
            else:
                raise RuntimeError(f"Ollama HTTP {resp.status_code}")

        except Exception as err:
            logger.warning(f"Ollama summarization failed: {err}, trying NVIDIA")
            # --- Fallback: NVIDIA cloud API ---
            try:
                from app.services.nvidia_api import NvidiaAPI

                nvidia = NvidiaAPI()
                completion = await nvidia.generate(
                    model=model_id,
                    prompt=prompt,
                    max_tokens=512,
                    temperature=0.3,
                )
                cc = completion.get("choices", [{}])[0].get("message", {})
                response_text = cc.get("content", "").strip()
                model_used = model_id
            except Exception as nerr:
                logger.error(f"NVIDIA summarization also failed: {nerr}")
                response_text = json.dumps(
                    {
                        "category": ActivityCategory.HOUSEKEEPING,
                        "summary": f"[AUTO-SUMMARY] {packet.title}: {packet.body[:200]}...",
                        "operator_relevance": Relevance.MEDIUM,
                        "needs_sean": True,
                        "suggested_surface": SuggestedSurface.CATCHUP,
                    }
                )
                model_used = "degraded-fallback"

        # --- Parse LLM response ---
        try:
            cleaned = response_text.strip()
            # Strip markdown code fences (```json ... ```) that Ollama may add
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            parsed = json.loads(cleaned)
            result.category = parsed.get("category", ActivityCategory.HOUSEKEEPING)
            result.summary = parsed.get("summary", response_text[:300])
            result.operator_relevance = parsed.get("operator_relevance", Relevance.LOW)
            result.needs_sean = parsed.get(
                "needs_sean", result.operator_relevance == Relevance.HIGH
            )
            result.suggested_surface = parsed.get(
                "suggested_surface", SuggestedSurface.NONE
            )
            result.confidence = (
                0.9 if result.category != ActivityCategory.HOUSEKEEPING else 0.7
            )
        except (json.JSONDecodeError, ValueError):
            result.category = ActivityCategory.VISIBILITY
            result.summary = response_text[:500]
            result.operator_relevance = Relevance.LOW
            result.needs_sean = False
            result.suggested_surface = SuggestedSurface.NONE
            result.confidence = 0.4

        result.model_used = model_used
        result.processing_time_ms = int(time.time() * 1000) - start_ms
        result.timestamp = datetime.now(timezone.utc).isoformat()
        return result

    async def process_batch(
        self, packets: List[ActivityInput]
    ) -> List[ActivitySummary]:
        """Process multiple activity packets in sequence."""
        results = []
        for packet in packets:
            try:
                results.append(await self.process(packet))
            except Exception as e:
                logger.error(f"Failed to process packet '{packet.title}': {e}")
                results.append(
                    ActivitySummary(
                        raw_input_kind=packet.kind,
                        repo_or_lane=packet.source,
                        category=ActivityCategory.HOUSEKEEPING,
                        summary=f"[ERROR] Failed to summarize: {str(e)[:200]}",
                        operator_relevance=Relevance.HIGH,
                        needs_sean=True,
                        suggested_surface=SuggestedSurface.CATCHUP,
                        confidence=0.0,
                    )
                )
        return results

    def to_json(self, summary: ActivitySummary) -> str:
        return json.dumps(asdict(summary), indent=2, default=str)

    def to_dict(self, summary: ActivitySummary) -> dict:
        return asdict(summary)


# --- Singleton accessor ---
_summarizer: Optional[ActivitySummarizer] = None


def get_summarizer() -> ActivitySummarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = ActivitySummarizer()
    return _summarizer
