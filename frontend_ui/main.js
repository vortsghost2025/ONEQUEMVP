// OneQueue Dashboard JavaScript
const API_BASE = '';

let currentFilter = 'all';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  fetchModels();
  loadTasks();
  loadQueueStatus();
  
  // Set up polling
  setInterval(checkHealth, 30000);
  setInterval(loadTasks, 5000);
  setInterval(loadQueueStatus, 10000);
  
  // Form handlers
  document.getElementById('chat-form').addEventListener('submit', handleChatSubmit);
  document.getElementById('task-form').addEventListener('submit', handleTaskSubmit);
  
  // Queue controls
  document.getElementById('btn-pause').addEventListener('click', () => controlQueue('pause'));
  document.getElementById('btn-resume').addEventListener('click', () => controlQueue('resume'));
  document.getElementById('btn-clear').addEventListener('click', () => controlQueue('clear-failed'));
  
  // Model filters
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      currentFilter = e.target.dataset.filter;
      fetchModels();
    });
  });
});

// Check System Health
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    
    if (data.status === 'healthy') {
      statusDot.classList.add('healthy');
      statusText.textContent = 'Healthy';
    } else {
      statusText.textContent = data.status || 'Unknown';
    }
  } catch (err) {
    document.getElementById('status-text').textContent = 'Offline';
  }
}

// Fetch and display models
async function fetchModels() {
  try {
    const res = await fetch(`${API_BASE}/v1/models`);
    const data = await res.json();
    const models = data.data || [];
    
    const filtered = currentFilter === 'all' 
      ? models 
      : models.filter(m => {
          const id = m.id.toLowerCase();
          return currentFilter === 'nvidia' ? id.includes('nvidia') : id.includes('ollama') || id.includes('llama3') || id.includes('mistral');
        });
    
    const list = document.getElementById('model-list');
    const chatSelect = document.getElementById('chat-model');
    const taskSelect = document.getElementById('task-model');
    
    list.innerHTML = '';
    const chatOptions = [];
    const taskOptions = [];
    
    filtered.forEach(m => {
      // Model list
      const li = document.createElement('li');
      const provider = m.owned_by || 'unknown';
      li.innerHTML = `
        <span class="model-name">${m.id}</span>
        <span class="model-provider">${provider}</span>
      `;
      list.appendChild(li);
      
      // Select options
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.id;
      chatOptions.push(opt.cloneNode(true));
      taskOptions.push(opt.cloneNode(true));
    });
    
    chatSelect.innerHTML = '<option value="auto">auto (smart routing)</option>';
    taskSelect.innerHTML = '';
    chatOptions.forEach(o => chatSelect.appendChild(o));
    taskOptions.forEach(o => taskSelect.appendChild(o));
    
  } catch (err) {
    console.error('Failed to fetch models:', err);
  }
}

// Load tasks
async function loadTasks() {
  try {
    const res = await fetch(`${API_BASE}/tasks`);
    const tasks = await res.json();
    
    const tbody = document.getElementById('task-table-body');
    tbody.innerHTML = '';
    
    tasks.forEach(t => {
      const tr = document.createElement('tr');
      const statusClass = t.status ? t.status.toLowerCase() : 'pending';
      tr.innerHTML = `
        <td>${t.id || 'N/A'}</td>
        <td>${t.model || 'N/A'}</td>
        <td><span class="status-badge ${statusClass}">${t.status || 'pending'}</span></td>
        <td>${truncate(t.result || '', 50)}</td>
      `;
      tbody.appendChild(tr);
    });
    
    // Update stats
    const stats = {
      total: tasks.length,
      pending: tasks.filter(t => t.status === 'pending').length,
      completed: tasks.filter(t => t.status === 'completed').length,
      failed: tasks.filter(t => t.status === 'failed').length
    };
    
    document.getElementById('stats').innerHTML = `
      <div class="stat-item"><div class="stat-value">${stats.total}</div><div class="stat-label">Total</div></div>
      <div class="stat-item"><div class="stat-value">${stats.pending}</div><div class="stat-label">Pending</div></div>
      <div class="stat-item"><div class="stat-value">${stats.completed}</div><div class="stat-label">Completed</div></div>
      <div class="stat-item"><div class="stat-value">${stats.failed}</div><div class="stat-label">Failed</div></div>
    `;
    
  } catch (err) {
    console.error('Failed to load tasks:', err);
  }
}

// Load queue status
async function loadQueueStatus() {
  try {
    const res = await fetch(`${API_BASE}/queue/status`);
    const data = await res.json();
    
    document.getElementById('queue-status').innerHTML = `
      <p>Status: ${data.status || 'unknown'}</p>
      <p>Queue Size: ${data.queue_size || 0}</p>
    `;
  } catch (err) {
    console.error('Failed to load queue status:', err);
  }
}

// Handle chat submit
async function handleChatSubmit(e) {
  e.preventDefault();
  
  const model = document.getElementById('chat-model').value;
  const prompt = document.getElementById('chat-prompt').value;
  const responseArea = document.getElementById('chat-response');
  
  responseArea.classList.add('loading');
  responseArea.textContent = 'Sending...';
  
  // Use smart router endpoint for "auto" model
  const endpoint = model === 'auto' ? '/router/v1/chat/completions' : '/v1/chat/completions';
  
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: model,
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 500
      })
    });
    
    const data = await res.json();
    responseArea.classList.remove('loading');
    
    if (data.choices && data.choices[0]) {
      responseArea.textContent = data.choices[0].message.content;
    } else if (data.detail) {
      responseArea.textContent = `Error: ${data.detail}`;
    } else {
      responseArea.textContent = JSON.stringify(data, null, 2);
    }
  } catch (err) {
    responseArea.classList.remove('loading');
    responseArea.textContent = `Error: ${err.message}`;
  }
}

// Handle task submit
async function handleTaskSubmit(e) {
  e.preventDefault();
  
  const model = document.getElementById('task-model').value;
  const prompt = document.getElementById('task-prompt').value;
  
  try {
    await fetch(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, prompt })
    });
    
    document.getElementById('task-prompt').value = '';
    loadTasks();
  } catch (err) {
    console.error('Failed to create task:', err);
  }
}

// Queue control
async function controlQueue(action) {
  try {
    await fetch(`${API_BASE}/queue/${action}`, { method: 'POST' });
    loadQueueStatus();
  } catch (err) {
    console.error(`Failed to ${action} queue:`, err);
  }
}

// Utility
function truncate(str, len) {
  if (!str) return '';
  return str.length > len ? str.substring(0, len) + '...' : str;
}