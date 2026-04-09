// Vanilla JS dashboard for OneQueue
const apiBase = ""; // relative to same host

async function fetchModels() {
  const res = await fetch(`${apiBase}/v1/models`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.data || [];
}

function populateModels(models) {
  const list = document.getElementById('model-list');
  const select = document.getElementById('model');
  list.innerHTML = '';
  select.innerHTML = '';
  models.forEach(m => {
    const li = document.createElement('li');
    li.textContent = `${m.id} - ${m.object || ''}`;
    list.appendChild(li);
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = m.id;
    select.appendChild(opt);
  });
}

async function loadTasks() {
  const res = await fetch(`${apiBase}/tasks`);
  const data = await res.json();
  const tbody = document.getElementById('task-table-body');
  tbody.innerHTML = '';
  data.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${t.id}</td><td>${t.model}</td><td>${t.prompt}</td><td>${t.status}</td><td>${t.result || ''}</td>`;
    tbody.appendChild(tr);
  });
}

async function createTask(event) {
  event.preventDefault();
  const model = document.getElementById('model').value;
  const prompt = document.getElementById('prompt').value;
  const payload = { model, prompt };
  await fetch(`${apiBase}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  document.getElementById('prompt').value = '';
  await loadTasks();
}

document.getElementById('task-form').addEventListener('submit', createTask);

// Initial load
(async () => {
  const models = await fetchModels();
  populateModels(models);
  await loadTasks();
  // Poll tasks every 5 seconds to update status
  setInterval(loadTasks, 5000);
})();
