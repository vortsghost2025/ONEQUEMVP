"""
Demo: Run ONE WE4FREE Activity Summarizer on a REAL packet.

This script processes a genuine archivist/headless runtime snapshot
through the full summarizer pipeline (Ollama → NVIDIA → degraded fallback)
and saves structured evidence for evaluation.

Usage:
    python scripts/demo_real_we4free_packet.py

Output:
    evidence/activity-summarizer/headless-autonomy-real-packet-2026-05-15.json
"""

import json
import os
import sys
import asyncio
from datetime import datetime, timezone

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workflows.activity_summarizer import (
    ActivityInput,
    ActivitySummarizer,
    get_summarizer,
)


# ─── The real packet ───────────────────────────────────────────────
PACKET = ActivityInput(
    kind="runtime_snapshot",
    source="lane:archivist/headless",
    title="Headless autonomous substrate corrected and runtime-verified",
    body="""\
OUTPUT_PROVENANCE:
agent: z-ai/glm5
lane: archivist
generated_at: 2026-05-15T00:35:00Z
session_id: archivist-session-20260514

Runtime status snapshot for exterior verification. All claims now have
verifiable evidence:
- 18 active services — listed by name
- 10 stopped duplicates — all active=inactive, enabled=disabled
- 4/4 lanes OK_HK — supervision board confirms
- 16 archived outbox messages (7 archivist + 9 kernel)
- 48 node processes (down from ~65 before duplicate removal)
- 86400s (24h) throttle — in CI loop script

The "strangely synchronized, noisy, agent-like" behavior was real autonomous
runtime — but with false complexity from duplicates, broken broadcast, and
health misclassification. Fixing those does not remove the autonomy; it makes
it legible.""",
)


def build_evidence_filename(summary):
    """Build a descriptive evidence filename from the summary."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    kind = summary.raw_input_kind.replace("/", "-")
    cat = summary.category
    return f"headless-autonomy-{kind}-{cat}-{ts}.json"


def run_evaluation(summary):
    """Evaluate the summary against the rubric."""
    eval_notes = []

    # Category check
    good_cats = {"autonomy", "repair", "visibility"}
    if summary.category in good_cats:
        eval_notes.append(f"CATEGORY GOOD: '{summary.category}' is semantically appropriate")
    else:
        eval_notes.append(
            f"CATEGORY WEAK: '{summary.category}' — expected autonomy/repair/visibility"
        )

    # Relevance check
    if summary.operator_relevance in ("medium", "high"):
        eval_notes.append(
            f"RELEVANCE GOOD: '{summary.operator_relevance}' — appropriate for Pulse"
        )
    else:
        eval_notes.append(
            f"RELEVANCE LOW: '{summary.operator_relevance}' — may be under-weighted"
        )

    # Surface recommendation
    if summary.suggested_surface == "Pulse":
        eval_notes.append("SURFACE: Pulse — correct for high/cross-cutting visibility")
    elif summary.suggested_surface == "CatchUp":
        eval_notes.append(
            "SURFACE: CatchUp — reasonable for medium-relevance batch-able items"
        )
    else:
        eval_notes.append(
            f"SURFACE: {summary.suggested_surface} — consider Pulse for this kind of operational update"
        )

    # needs_sean assessment
    if not summary.needs_sean:
        eval_notes.append(
            "needs_sean=False — appropriate if system is self-healing and verified"
        )
    else:
        eval_notes.append("needs_sean=True — might be over-flagging routine autonomy events")

    # Confidence assessment
    if summary.confidence >= 0.7:
        eval_notes.append(f"CONFIDENCE: {summary.confidence:.1f} — usable for Pulse")
    elif summary.confidence >= 0.4:
        eval_notes.append(f"CONFIDENCE: {summary.confidence:.1f} — marginal, needs review")
    else:
        eval_notes.append(f"CONFIDENCE: {summary.confidence:.1f} — too low for production")

    return eval_notes


async def main():
    os.makedirs("evidence/activity-summarizer", exist_ok=True)

    print("=" * 70)
    print("WE4FREE ACTIVITY SUMMARIZER — REAL PACKET DEMO")
    print("=" * 70)
    print()
    print(f"Kind:        {PACKET.kind}")
    print(f"Source:      {PACKET.source}")
    print(f"Title:       {PACKET.title}")
    print(f"Body length: {len(PACKET.body)} chars")
    print()

    summarizer = get_summarizer()

    # Process the real packet
    summary = await summarizer.process(PACKET)

    # Print structured output
    print("─" * 70)
    print("STRUCTURED OUTPUT (JSON):")
    print("─" * 70)
    output_json = summarizer.to_json(summary)
    print(output_json)
    print()

    # Run evaluation
    print("─" * 70)
    print("EVALUATION AGAINST RUBRIC:")
    print("─" * 70)
    eval_notes = run_evaluation(summary)
    for i, note in enumerate(eval_notes, 1):
        print(f"  {i}. {note}")
    print()

    # Diagnostic info
    print("─" * 70)
    print("DIAGNOSTICS:")
    print("─" * 70)
    print(f"  Model used:          {summary.model_used}")
    print(f"  Processing time:     {summary.processing_time_ms}ms")
    print(f"  Confidence:          {summary.confidence}")
    print(f"  Timestamp:           {summary.timestamp}")

    # Determine engine path taken
    if "degraded" in summary.model_used.lower():
        engine_path = "DEGRADED FALLBACK (both Ollama and NVIDIA failed)"
    elif summary.model_used.startswith("qwen"):
        engine_path = "LOCAL OLLAMA (qwen2.5-coder)"
    else:
        engine_path = f"NIKE/UNKNOWN ({summary.model_used})"
    print(f"  Engine path:         {engine_path}")
    print()

    # Save evidence
    evidence = {
        "packet": {
            "kind": PACKET.kind,
            "source": PACKET.source,
            "title": PACKET.title,
            "body": PACKET.body,
        },
        "summary": {
            "id": summary.id,
            "category": summary.category,
            "repo_or_lane": summary.repo_or_lane,
            "summary_text": summary.summary,
            "operator_relevance": summary.operator_relevance,
            "needs_sean": summary.needs_sean,
            "suggested_surface": summary.suggested_surface,
            "model_used": summary.model_used,
            "processing_time_ms": summary.processing_time_ms,
            "timestamp": summary.timestamp,
            "raw_input_kind": summary.raw_input_kind,
            "confidence": summary.confidence,
        },
        "evaluation": eval_notes,
        "engine_path": engine_path,
        "demo_run_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = os.path.join("evidence/activity-summarizer", build_evidence_filename(summary))
    with open(out_path, "w") as f:
        json.dump(evidence, f, indent=2)
    print(f"Evidence saved to: {out_path}")
    print()
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())