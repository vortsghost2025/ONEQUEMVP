"""Demo: Run ONE WE4FREE Activity Summarizer on a REAL packet."""
import json, os, sys, asyncio
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workflows.activity_summarizer import ActivityInput, get_summarizer

PACKET = ActivityInput(
    kind="runtime_snapshot",
    source="lane:archivist/headless",
    title="Headless autonomous substrate corrected and runtime-verified",
    body=(
        "OUTPUT_PROVENANCE:\n"
        "agent: z-ai/glm5\n"
        "lane: archivist\n"
        "generated_at: 2026-05-15T00:35:00Z\n"
        "session_id: archivist-session-20260514\n\n"
        "Runtime status snapshot for exterior verification. All claims now have "
        "verifiable evidence:\n"
        "- 18 active services listed by name\n"
        "- 10 stopped duplicates all active=inactive, enabled=disabled\n"
        "- 4/4 lanes OK_HK supervision board confirms\n"
        "- 16 archived outbox messages (7 archivist + 9 kernel)\n"
        "- 48 node processes (down from 65 before duplicate removal)\n"
        "- 86400s (24h) throttle in CI loop script\n\n"
        "The strangely synchronized noisy agent-like behavior was real autonomous "
        "runtime but with false complexity from duplicates, broken broadcast, and "
        "health misclassification. Fixing those does not remove the autonomy; "
        "it makes it legible."
    ),
)

def evaluate(s):
    notes = []
    cats = {"autonomy", "repair", "visibility"}
    notes.append(("GOOD" if s.category in cats else "WEAK") + ": category=" + s.category)
    notes.append(("GOOD" if s.operator_relevance in ("medium","high") else "LOW") + ": relevance=" + s.operator_relevance)
    notes.append("surface=" + s.suggested_surface)
    notes.append("needs_sean=" + str(s.needs_sean))
    notes.append("confidence=" + str(s.confidence))
    return notes

async def main():
    os.makedirs("evidence/activity-summarizer", exist_ok=True)
    sep = "=" * 60
    print(sep)
    print("WE4FREE ACTIVITY SUMMARIZER - REAL PACKET DEMO")
    print(sep)
    print("Kind:", PACKET.kind)
    print("Source:", PACKET.source)
    print("Title:", PACKET.title)
    print("Body:", len(PACKET.body), "chars")
    print()

    summ = get_summarizer()
    summary = await summ.process(PACKET)

    print(sep)
    print("STRUCTURED OUTPUT:")
    print(sep)
    out = summ.to_json(summary)
    print(out)
    print()

    print(sep)
    print("EVALUATION:")
    print(sep)
    for n in evaluate(summary):
        print(" ", n)
    print()

    print(sep)
    print("DIAGNOSTICS:")
    print(sep)
    eng = "DEGRADED" if "degraded" in (summary.model_used or "").lower() else ("OLLAMA" if summary.model_used and "qwen" in summary.model_used else "UNKNOWN")
    print("Model used:", summary.model_used)
    print("Engine path:", eng)
    print("Processing time:", summary.processing_time_ms, "ms")
    print("Confidence:", summary.confidence)
    print("Timestamp:", summary.timestamp)
    print()

    evidence = {
        "packet": {"kind": PACKET.kind, "source": PACKET.source, "title": PACKET.title, "body": PACKET.body},
        "summary": {
            "id": summary.id, "category": summary.category,
            "repo_or_lane": summary.repo_or_lane, "summary_text": summary.summary,
            "operator_relevance": summary.operator_relevance, "needs_sean": summary.needs_sean,
            "suggested_surface": summary.suggested_surface, "model_used": summary.model_used,
            "processing_time_ms": summary.processing_time_ms, "timestamp": summary.timestamp,
            "raw_input_kind": summary.raw_input_kind, "confidence": summary.confidence,
        },
        "evaluation": evaluate(summary),
        "engine_path": eng,
    }

    fpath = os.path.join("evidence/activity-summarizer", "headless-autonomy-demo-" + datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".json")
    with open(fpath, "w") as f:
        json.dump(evidence, f, indent=2)
    print("Evidence saved to:", fpath)
    print(sep)
    print("DEMO COMPLETE")
    print(sep)

if __name__ == "__main__":
    asyncio.run(main())
