import { useState, useEffect } from 'react';
import './App.css';
import NvidiaTest from './NvidiaTest';
import ModelSelector from './ModelSelector';
import HealthDashboard from './HealthDashboard';
import AIdeaChat from './components/AIdeaChat';
import {
  getQueueStatus,
  pauseQueue,
  resumeQueue,
  clearFailed,
  getTasks,
  createTask,
  cancelTask,
  retryTask,
  getSettings,
  updateSettings,
  getSystemHealth,
} from './api';

const POLL_INTERVAL = 3000;

export default function App() {
  const [queue, setQueue] = useState({ queue_paused: false, pending_count: 0, running_count: 0 });
  const [tasks, setTasks] = useState([]);
const [newTask, setNewTask] = useState({ title: '', prompt: '', model: 'auto', timeout_seconds: 120 });
const [settings, setSettings] = useState({ max_ram_percent: 85, max_cpu_percent: 90, breach_duration_seconds: 5 });
const [loading, setLoading] = useState(false);
const [activeTab, setActiveTab] = useState('tasks');
const [recommendedModel, setRecommendedModel] = useState(null);
const [healthStatus, setHealthStatus] = useState({ backend: 'unknown', ollama: 'unknown', nvidia_api: 'unknown' });

const HEALTH_POLL_INTERVAL = 10000;

  useEffect(() => {
    const fetchQueue = async () => {
      try {
        const data = await getQueueStatus();
        setQueue(data);
      } catch (e) {
        console.error('Queue status error', e);
      }
    };
    fetchQueue();
    const id = setInterval(fetchQueue, POLL_INTERVAL);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const data = await getTasks();
        setTasks(data);
      } catch (e) {
        console.error('Tasks load error', e);
      }
    };
    fetchTasks();
    const id = setInterval(fetchTasks, POLL_INTERVAL);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const s = await getSettings();
        setSettings({
          max_ram_percent: s.max_ram_percent,
          max_cpu_percent: s.max_cpu_percent,
          breach_duration_seconds: s.breach_duration_seconds
        });
      } catch (e) {
        console.error('Settings load error', e);
      }
    };
    load();
  }, []);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getSystemHealth();
        setHealthStatus({
          backend: data.backend || 'unknown',
          ollama: data.ollama || 'unknown',
          nvidia_api: data.nvidia_api || 'unknown'
        });
      } catch (e) {
        setHealthStatus({ backend: 'down', ollama: 'unknown', nvidia_api: 'unknown' });
      }
    };
    fetchHealth();
    const id = setInterval(fetchHealth, HEALTH_POLL_INTERVAL);
    return () => clearInterval(id);
  }, []);

  const handlePause = async () => {
    await pauseQueue();
    const data = await getQueueStatus();
    setQueue(data);
  };

  const handleResume = async () => {
    await resumeQueue();
    const data = await getQueueStatus();
    setQueue(data);
  };

  const handleClearFailed = async () => {
    await clearFailed();
    const data = await getTasks();
    setTasks(data);
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    if (!newTask.title || !newTask.prompt) return;

    setLoading(true);
    try {
      await createTask(newTask);
      setNewTask({ title: '', prompt: '', model: 'llama3', timeout_seconds: 120 });
      const data = await getTasks();
      setTasks(data);
    } catch (error) {
      console.error('Create task error:', error);
      alert('Failed to create task: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (id) => {
    await cancelTask(id);
    const data = await getTasks();
    setTasks(data);
  };

  const handleRetry = async (id) => {
    await retryTask(id);
    const data = await getTasks();
    setTasks(data);
  };

  const handleSettingsChange = (e) => {
    const { name, value } = e.target;
    setSettings((prev) => ({ ...prev, [name]: Number(value) }));
  };

  const handleSettingsSave = async () => {
    await updateSettings({
      max_ram_percent: settings.max_ram_percent,
      max_cpu_percent: settings.max_cpu_percent,
      breach_duration_seconds: settings.breach_duration_seconds
    });
    const s = await getSettings();
    setSettings({
      max_ram_percent: s.max_ram_percent,
      max_cpu_percent: s.max_cpu_percent,
      breach_duration_seconds: s.breach_duration_seconds
    });
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      pending: { class: 'badge-pending', icon: '⏳', label: 'Pending' },
      running: { class: 'badge-running', icon: '▶️', label: 'Running' },
      completed: { class: 'badge-completed', icon: '✅', label: 'Completed' },
      failed: { class: 'badge-failed', icon: '❌', label: 'Failed' },
      cancelled: { class: 'badge-cancelled', icon: '🚫', label: 'Cancelled' },
    };
    const config = statusConfig[status] || { class: 'badge-default', icon: '•', label: status };
    return (
      <span className={`status-badge ${config.class}`} role="status" aria-label={config.label}>
        <span className="badge-icon" aria-hidden="true">{config.icon}</span>
        <span className="badge-text">{config.label}</span>
      </span>
    );
  };

  const getHealthDotColor = (status) => {
    if (status === 'healthy' || status === 'configured') return '#22c55e';
    if (status === 'offline' || status === 'down' || status === 'error_' || status === 'invalid_format') return '#ef4444';
    if (status === 'unknown' || status === 'missing_key') return '#eab308';
    return '#eab308';
  };

  const getHealthStatusLabel = (service, status) => {
    const labels = {
      backend: { healthy: 'Backend healthy', down: 'Backend down', unknown: 'Backend unknown' },
      ollama: { healthy: 'Ollama healthy', offline: 'Ollama offline', unknown: 'Ollama unknown' },
      nvidia_api: { configured: 'NVIDIA configured', missing_key: 'NVIDIA key missing', invalid_format: 'NVIDIA key invalid', unknown: 'NVIDIA unknown' }
    };
    return labels[service]?.[status] || `${service} ${status}`;
  };

  const pendingCount = tasks.filter(t => t.status === 'pending').length;
  const runningCount = tasks.filter(t => t.status === 'running').length;
  const completedCount = tasks.filter(t => t.status === 'completed').length;
  const failedCount = tasks.filter(t => t.status === 'failed').length;

  return (
    <div className="app-container">
<header className="app-header" role="banner">
<div className="header-content">
<div className="brand">
<h1 className="app-title">
<span className="title-icon" aria-hidden="true">⚡</span>
OneQueue
</h1>
<p className="app-subtitle">Universal Inference Router</p>
</div>

<HealthDashboard />

<nav className="queue-status-nav" aria-label="Queue status">
<div className={`status-indicator ${queue.queue_paused ? 'paused' : 'running'}`}>
<span className="status-dot" aria-hidden="true"></span>
<span className="status-label">{queue.queue_paused ? 'Paused' : 'Running'}</span>
</div>

<div className="health-indicators" aria-label="Service health status">
  <div className="health-indicator" title={getHealthStatusLabel('backend', healthStatus.backend)}>
    <span
      className="health-dot"
      style={{ backgroundColor: getHealthDotColor(healthStatus.backend) }}
      aria-label={getHealthStatusLabel('backend', healthStatus.backend)}
    />
  </div>
  <div className="health-indicator" title={getHealthStatusLabel('ollama', healthStatus.ollama)}>
    <span
      className="health-dot"
      style={{ backgroundColor: getHealthDotColor(healthStatus.ollama) }}
      aria-label={getHealthStatusLabel('ollama', healthStatus.ollama)}
    />
  </div>
  <div className="health-indicator" title={getHealthStatusLabel('nvidia_api', healthStatus.nvidia_api)}>
    <span
      className="health-dot"
      style={{ backgroundColor: getHealthDotColor(healthStatus.nvidia_api) }}
      aria-label={getHealthStatusLabel('nvidia_api', healthStatus.nvidia_api)}
    />
  </div>
</div>
            
            <div className="queue-metrics">
              <div className="metric">
                <span className="metric-value">{pendingCount}</span>
                <span className="metric-label">Pending</span>
              </div>
              <div className="metric">
                <span className="metric-value">{runningCount}</span>
                <span className="metric-label">Running</span>
              </div>
              <div className="metric">
                <span className="metric-value">{completedCount}</span>
                <span className="metric-label">Done</span>
              </div>
              {failedCount > 0 && (
                <div className="metric metric-error">
                  <span className="metric-value">{failedCount}</span>
                  <span className="metric-label">Failed</span>
                </div>
              )}
            </div>
          </nav>
          
          <div className="queue-actions">
            {queue.queue_paused ? (
              <button
                onClick={handleResume}
                className="btn btn-primary"
                aria-label="Resume queue"
              >
                <span className="btn-icon" aria-hidden="true">▶</span>
                Resume
              </button>
            ) : (
              <button
                onClick={handlePause}
                className="btn btn-secondary"
                aria-label="Pause queue"
              >
                <span className="btn-icon" aria-hidden="true">⏸</span>
                Pause
              </button>
            )}
            {failedCount > 0 && (
              <button
                onClick={handleClearFailed}
                className="btn btn-danger"
                aria-label="Clear failed tasks"
              >
                <span className="btn-icon" aria-hidden="true">🗑</span>
                Clear Failed
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="tabs-container">
          <div className="tabs" role="tablist">
            <button
              role="tab"
              aria-selected={activeTab === 'tasks'}
              className={`tab ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => setActiveTab('tasks')}
            >
              <span className="tab-icon" aria-hidden="true">📋</span>
              Tasks
            </button>
            <button
              role="tab"
              aria-selected={activeTab === 'create'}
              className={`tab ${activeTab === 'create' ? 'active' : ''}`}
              onClick={() => setActiveTab('create')}
            >
              <span className="tab-icon" aria-hidden="true">➕</span>
              Create Task
            </button>
<button
    role="tab"
    aria-selected={activeTab === 'ai'}
    className={`tab ${activeTab === 'ai' ? 'active' : ''}`}
    onClick={() => setActiveTab('ai')}
  >
    <span className="tab-icon" aria-hidden="true">💡</span>
    AI Ideas
  </button>
  <button
    role="tab"
    aria-selected={activeTab === 'nvidia'}
    className={`tab ${activeTab === 'nvidia' ? 'active' : ''}`}
    onClick={() => setActiveTab('nvidia')}
  >
    <span className="tab-icon" aria-hidden="true">🚀</span>
    NVIDIA
  </button>
  <button
    role="tab"
    aria-selected={activeTab === 'settings'}
    className={`tab ${activeTab === 'settings' ? 'active' : ''}`}
    onClick={() => setActiveTab('settings')}
  >
    <span className="tab-icon" aria-hidden="true">⚙️</span>
    Settings
  </button>
</div>
</div>

        {activeTab === 'create' && (
          <section className="panel create-panel" aria-labelledby="create-task-heading">
            <h2 id="create-task-heading" className="panel-title">Create New Task</h2>
            <form onSubmit={handleCreateTask} className="task-form">
              <div className="form-group">
                <label htmlFor="task-title" className="form-label">
                  Title
                </label>
                <input
                  id="task-title"
                  type="text"
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  required
                  aria-required="true"
                  className="form-input"
                  placeholder="Enter task title..."
                />
              </div>

              <div className="form-group">
                <label htmlFor="task-prompt" className="form-label">
                  Prompt
                </label>
                <textarea
                  id="task-prompt"
                  value={newTask.prompt}
                  onChange={(e) => setNewTask({ ...newTask, prompt: e.target.value })}
                  required
                  aria-required="true"
                  rows={6}
                  className="form-textarea"
                  placeholder="Enter your prompt..."
                />
              </div>

<div className="form-row">
<div className="form-group">
<label htmlFor="task-model" className="form-label">
Model
</label>
<ModelSelector
value={newTask.model}
onChange={(model) => setNewTask({ ...newTask, model })}
prompt={newTask.prompt}
showRecommendation={true}
/>
</div>

<div className="form-group">
<label htmlFor="task-timeout" className="form-label">
Timeout (seconds)
</label>
<input
id="task-timeout"
type="number"
value={newTask.timeout_seconds}
onChange={(e) => setNewTask({ ...newTask, timeout_seconds: Number(e.target.value) })}
min={1}
className="form-input"
/>
</div>
</div>

              <button
                type="submit"
                className="btn btn-primary btn-large"
                disabled={loading}
                aria-busy={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner" aria-hidden="true"></span>
                    Creating...
                  </>
                ) : (
                  <>
                    <span className="btn-icon" aria-hidden="true">➕</span>
                    Create Task
                  </>
                )}
              </button>
            </form>
          </section>
        )}

        {activeTab === 'tasks' && (
          <section className="panel tasks-panel" aria-labelledby="tasks-heading">
            <h2 id="tasks-heading" className="panel-title">Task Queue</h2>
            <div className="tasks-table-container" role="region" aria-label="Tasks table" tabIndex={0}>
              {tasks.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon" aria-hidden="true">📭</div>
                  <h3>No tasks yet</h3>
                  <p>Create your first task to get started</p>
                  <button
                    className="btn btn-primary"
                    onClick={() => setActiveTab('create')}
                  >
                    Create Task
                  </button>
                </div>
              ) : (
                <table className="tasks-table">
                  <thead>
                    <tr>
                      <th scope="col">Title</th>
                      <th scope="col">Status</th>
                      <th scope="col">Priority</th>
                      <th scope="col">Attempts</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((task) => (
                      <tr key={task.id}>
                        <td className="task-title-cell">
                          <div className="task-title">{task.title}</div>
                          <div className="task-model">{task.model}</div>
                        </td>
                        <td>{getStatusBadge(task.status)}</td>
                        <td className="task-priority">{task.priority}</td>
                        <td className="task-attempts">{task.attempt_count}</td>
                        <td className="task-actions">
                          {task.status === 'pending' && (
                            <button
                              onClick={() => handleCancel(task.id)}
                              className="btn btn-small btn-secondary"
                              aria-label={`Cancel task ${task.title}`}
                            >
                              Cancel
                            </button>
                          )}
                          {task.status === 'failed' && (
                            <button
                              onClick={() => handleRetry(task.id)}
                              className="btn btn-small btn-primary"
                              aria-label={`Retry task ${task.title}`}
                            >
                              Retry
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        )}

{activeTab === 'ai' && (
        <section className="panel ai-panel" aria-labelledby="ai-heading">
          <AIdeaChat onTasksCreated={fetchTasks} />
        </section>
      )}

      {activeTab === 'nvidia' && (
        <section className="panel nvidia-panel" aria-labelledby="nvidia-heading">
          <h2 id="nvidia-heading" className="panel-title">NVIDIA Models</h2>
          <NvidiaTest />
        </section>
      )}

{activeTab === 'settings' && (
<section className="panel settings-panel" aria-labelledby="settings-heading">
<h2 id="settings-heading" className="panel-title">Settings</h2>
            <div className="settings-form">
              <div className="form-group">
                <label htmlFor="max-ram" className="form-label">
                  Max RAM Percentage
                </label>
                <input
                  id="max-ram"
                  type="number"
                  name="max_ram_percent"
                  value={settings.max_ram_percent}
                  onChange={handleSettingsChange}
                  min={0}
                  max={100}
                  className="form-input"
                />
                <p className="form-hint">Queue pauses when RAM exceeds this threshold</p>
              </div>

              <div className="form-group">
                <label htmlFor="max-cpu" className="form-label">
                  Max CPU Percentage
                </label>
                <input
                  id="max-cpu"
                  type="number"
                  name="max_cpu_percent"
                  value={settings.max_cpu_percent}
                  onChange={handleSettingsChange}
                  min={0}
                  max={100}
                  className="form-input"
                />
                <p className="form-hint">Queue pauses when CPU exceeds this threshold</p>
              </div>

              <div className="form-group">
                <label htmlFor="breach-duration" className="form-label">
                  Breach Duration (seconds)
                </label>
                <input
                  id="breach-duration"
                  type="number"
                  name="breach_duration_seconds"
                  value={settings.breach_duration_seconds}
                  onChange={handleSettingsChange}
                  min={1}
                  max={60}
                  className="form-input"
                />
                <p className="form-hint">How long thresholds must be exceeded before pausing</p>
              </div>

              <button
                onClick={handleSettingsSave}
                className="btn btn-primary"
              >
                <span className="btn-icon" aria-hidden="true">💾</span>
                Save Settings
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
