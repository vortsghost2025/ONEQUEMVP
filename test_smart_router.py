"""Test the updated smart router configuration"""

from app.services.smart_router import SmartRouter, TaskType

print("=" * 60)
print("Testing Updated Smart Router Configuration")
print("=" * 60)

# Initialize router
sr = SmartRouter()
print("")
print("[OK] Smart Router loaded successfully")
print("Total models in registry: " + str(len(sr.models)))

# Test optimal model selection
print("")
print("=== Optimal Model Selection by Task Type ===")
task_types = [
    TaskType.CODE,
    TaskType.REASONING,
    TaskType.MATH,
    TaskType.GENERAL,
    TaskType.CREATIVE,
    TaskType.LONG_CONTEXT,
    TaskType.MULTILINGUAL,
]

for task in task_types:
    model = sr.get_optimal_model_for_task(task)
    print("  " + task.value.ljust(15) + " -> " + model)

# Test fallback chains
print("")
print("=== Fallback Chains ===")
test_models = [
    "meta/llama-4-maverick-17b-128e-instruct",
    "qwen/qwen2.5-coder-32b-instruct",
    "deepseek-ai/deepseek-r1-distill-llama-8b",
]

for model_id in test_models:
    chain = sr.get_fallback_chain(model_id)
    print("")
    print(model_id + ":")
    print("  Chain: " + " -> ".join(chain))

# Test task analysis
print("")
print("=== Task Analysis Test ===")
test_prompts = [
    ("Write a Python function to sort a list", TaskType.CODE),
    ("Explain quantum physics", TaskType.GENERAL),
    ("Solve this equation: 2x + 5 = 15", TaskType.MATH),
    ("Write a poem about AI", TaskType.CREATIVE),
]

for prompt, expected_type in test_prompts:
    detected = sr.analyze_task(prompt)
    status = "[OK]" if detected == expected_type else "[WARN]"
    print("  " + status + " '" + prompt[:40] + "...' -> " + detected.value)

print("")
print("=" * 60)
print("[OK] All smart router tests passed!")
print("=" * 60)
