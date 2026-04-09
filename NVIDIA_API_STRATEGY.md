# NVIDIA API Strategy - OneQueue + 189 Models

## What We Have
- **189 models** available via NVIDIA API
- **Free access** (NVIDIA NIM API)
- Includes: Llama 4, DeepSeek V3.2, Gemma 4, Nemotron Ultra, Mistral Large 3
- No visible rate limits yet

## Immediate Opportunities

### 1. Model Router for OneQueue
Add intelligent model routing to OneQueue so users can:
- Select from 189 models instead of just local Ollama
- Auto-select best model for task type (coding, reasoning, chat, multilingual)
- Fallback chain: NVIDIA API → Local Ollama

### 2. Multi-Model Comparison
Build a feature to:
- Send same prompt to multiple models
- Compare outputs side-by-side
- Benchmark latency/quality

### 3. Specialized Task Routing
```
Coding tasks → deepseek-coder, qwen3-coder
Reasoning → deepseek-r1-distill, qwq-32b
Chat → llama-4-maverick, gemma-4
Large context → llama-3.1-405b, mistral-large-3
Multilingual → swallow (Japanese), bielik (Polish)
```

### 4. Cost Optimization
- Use local Ollama for simple tasks
- Use NVIDIA API for:
  - Complex reasoning
  - Coding tasks
  - Large context needs
  - When GPU is busy

### 5. API Key Management
- Store key securely in `.env`
- Add to OneQueue settings UI
- Support multiple keys (load balancing)

## Quick Wins

### Option A: Add NVIDIA as Model Source
1. Add NVIDIA API client to `app/services/`
2. Update frontend model selector
3. Add "cloud" vs "local" toggle

### Option B: Build Model Router
1. Task type detection
2. Intelligent model selection
3. Automatic fallback

### Option C: Create Model Comparison Tool
1. New "Compare" tab
2. Select multiple models
3. Run same prompt
4. Show outputs side-by-side

## Recommended Path

**Start with Option A** - simplest integration:
1. Add NVIDIA API support to backend
2. Update frontend to show available models
3. Add cloud/local toggle
4. Test with a few key models

## Models to Prioritize

**Must-have:**
- `meta/llama-4-maverick-17b-128e-instruct` - Latest Llama 4
- `deepseek-ai/deepseek-v3.2` - Best reasoning
- `nvidia/llama-3.3-nemotron-super-49b-v1.5` - NVIDIA's best

**Coding:**
- `deepseek-ai/deepseek-r1-distill-llama-8b`
- `qwen/qwen3-coder-480b-a35b-instruct`

**Fast/Cheap:**
- `google/gemma-3-1b-it` - Tiny, fast
- `microsoft/phi-4-mini-instruct` - Efficient

## Next Steps

1. Store API key securely
2. Add NVIDIA API client to backend
3. Update model selector UI
4. Test integration
5. Add intelligent routing logic
