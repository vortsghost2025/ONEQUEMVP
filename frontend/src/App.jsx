import { useState, useEffect } from 'react';
import './App.css';
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
} from './api';

const POLL_INTERVAL = 3000;

export default function App() {
  const [queue, setQueue] = useState({ queue_paused: false, pending_count: 0, running_count: 0 });
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState({ title: '', prompt: '', model: 'llama3', timeout_seconds: 120 });
  const [settings, setSettings] = useState({ max_ram_percent: 85, max_cpu_percent: 90, breach_duration_seconds: 5 });
  const [loading, setLoading] = useState(false);

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

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <span className="status-icon pending" aria-label="Pending">Pending</span>;
      case 'running':
        return <span className="status-icon running" aria-label="Running">Running</span>;
      case 'completed':
        return <span className="status-icon completed" aria-label="Completed">Completed</span>;
      case 'failed':
        return <span className="status-icon failed" aria-label="Failed">Failed</span>;
      case 'cancelled':
        return <span className="status-icon cancelled" aria-label="Cancelled">Cancelled</span>;
      default:
        return <span className="status-icon" aria-label={status}>{status}</span>;
    }
  };

  return (
    <div className="app-container">
      <header className="queue-bar" role="banner">
        <div className="queue-status">
          <strong>Queue:</strong>{' '}
          <span className={queue.queue_paused ? 'status-paused' : 'status-running'}>
            {queue.queue_paused ? 'Paused' : 'Running'}
          </span>
          <span className="separator">|</span>
          <strong>Pending:</strong> {queue.pending_count}
          <span className="separator">|</span>
          <strong>Running:</strong> {queue.running_count}
        </div>
        <div className="queue-controls">
          {queue.queue_paused ? (
            <button 
              onClick={handleResume}
              className="btn btn-primary"
              aria-label="Resume queue"
            >
              Resume
            </button>
          ) : (
            <button 
              onClick={handlePause}
              className="btn btn-secondary"
              aria-label="Pause queue"
            >
              Pause
            </button>
          )}
          <button 
            onClick={handleClearFailed}
            className="btn btn-warning"
            aria-label="Clear failed tasks"
          >
            Clear Failed
          </button>
        </div>
      </header>

      <main className="main-content">
        <section className="task-form" aria-labelledby="create-task-heading">
          <h3 id="create-task-heading">Create Task</h3>
          <form onSubmit={handleCreateTask}>
            <div className="form-group">
              <label htmlFor="task-title">
                Title:
                <input
                  id="task-title"
                  type="text"
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  required
                  aria-required="true"
                />
              </label>
            </div>
            
            <div className="form-group">
              <label htmlFor="task-prompt">
                Prompt:
                <textarea
                  id="task-prompt"
                  value={newTask.prompt}
                  onChange={(e) => setNewTask({ ...newTask, prompt: e.target.value })}
                  required
                  rows={4}
                  aria-required="true"
                />
              </label>
            </div>
            
            <div className="form-group">
              <label htmlFor="task-model">
                Model:
                <input
                  id="task-model"
                  type="text"
                  value={newTask.model}
                  onChange={(e) => setNewTask({ ...newTask, model: e.target.value })}
                />
              </label>
            </div>
            
            <div className="form-group">
              <label htmlFor="task-timeout">
                Timeout (seconds):
                <input
                  id="task-timeout"
                  type="number"
                  value={newTask.timeout_seconds}
                  onChange={(e) => setNewTask({ ...newTask, timeout_seconds: Number(e.target.value) })}
                  min={1}
                />
              </label>
            </div>
            
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={loading}
              aria-busy={loading}
            >
              {loading ? 'Creating...' : 'Create Task'}
            </button>
          </form>
        </section>

        <section className="tasks-list" aria-labelledby="tasks-heading">
          <h3 id="tasks-heading">Tasks</h3>
          <div role="region" aria-label="Tasks table" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Titl
