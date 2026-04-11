// src/api.js
// OneQueue backend API - port should match uvicorn startup

const BASE_URL = 'http://127.0.0.1:8081';

async function handleResponse(response) {
  if (!response.ok) {
    const err = await response.text();
    throw new Error('HTTP ' + response.status + ': ' + err);
  }
  return response.json();
}

// Settings
export async function getSettings() {
  return handleResponse(await fetch(BASE_URL + '/settings'));
}
export async function updateSettings(payload) {
  return handleResponse(await fetch(BASE_URL + '/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }));
}

// Queue control
export async function getQueueStatus() {
  return handleResponse(await fetch(BASE_URL + '/queue/status'));
}
export async function pauseQueue() {
  return handleResponse(await fetch(BASE_URL + '/queue/pause', { method: 'POST' }));
}
export async function resumeQueue() {
  return handleResponse(await fetch(BASE_URL + '/queue/resume', { method: 'POST' }));
}
export async function clearFailed() {
  return handleResponse(await fetch(BASE_URL + '/queue/clear-failed', { method: 'POST' }));
}

// Tasks
export async function getTasks() {
  return handleResponse(await fetch(BASE_URL + '/tasks'));
}
export async function createTask(payload) {
  return handleResponse(await fetch(BASE_URL + '/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }));
}
export async function cancelTask(id) {
  return handleResponse(await fetch(BASE_URL + '/tasks/' + id + '/cancel', { method: 'POST' }));
}
export async function retryTask(id) {
  return handleResponse(await fetch(BASE_URL + '/tasks/' + id + '/retry', { method: 'POST' }));
}

// NVIDIA API
export async function getNvidiaModels() {
  return handleResponse(await fetch(BASE_URL + '/nvidia/models'));
}

export async function getCuratedModels() {
  return handleResponse(await fetch(BASE_URL + '/nvidia/curated'));
}

export async function generateNvidia(model, prompt, options = {}) {
  return handleResponse(await fetch(BASE_URL + '/nvidia/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, prompt, ...options }),
  }));
}

// Smart Router API
export async function getSmartRoute(prompt) {
  return handleResponse(await fetch(BASE_URL + '/router/route', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  }));
}

export async function getRecommendedModels(taskType = null) {
  const url = taskType 
    ? `${BASE_URL}/router/models/recommended?task_type=${taskType}`
    : `${BASE_URL}/router/models/recommended`;
  return handleResponse(await fetch(url));
}

export async function getAllModels() {
  return handleResponse(await fetch(BASE_URL + '/v1/models'));
}

export async function getModelInfo(modelId) {
  return handleResponse(await fetch(`${BASE_URL}/router/models/${encodeURIComponent(modelId)}`));
}

export async function getFallbackChain(modelId) {
  return handleResponse(await fetch(`${BASE_URL}/router/fallback/${encodeURIComponent(modelId)}`));
}

// Benchmark API
export async function runQuickBenchmark() {
  return handleResponse(await fetch(BASE_URL + '/router/benchmark/quick', {
    method: 'POST',
  }));
}

export async function getBenchmarkResults() {
  return handleResponse(await fetch(BASE_URL + '/router/benchmark/results'));
}

// OpenAI-compatible API
export async function openaiChat(messages, model = 'auto', options = {}) {
  return handleResponse(await fetch(BASE_URL + '/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      messages,
      ...options
    }),
  }));
}

// System Health
export async function getSystemHealth() {
  return handleResponse(await fetch(BASE_URL + '/queue/health'));
}

// Check Ollama availability
export async function checkOllamaHealth() {
  try {
    const response = await fetch(BASE_URL.replace('8081', '11434') + '/api/tags', { method: 'GET' });
    return response.ok;
  } catch {
    return false;
  }
}

// Check NVIDIA API availability
export async function getNvidiaHealth() {
  return { configured: !!localStorage.getItem('nvidia_api_key') || !!sessionStorage.getItem('nvidia_api_key') };
}
