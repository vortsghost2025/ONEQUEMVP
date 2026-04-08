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

const POLL_INTERVAL = 3000; // ms

export default function App() {
  // Queue state
  const [queue, setQueue] = useState({ queue_paused: false, pending_count: 0, running_count: 0 });
  // Tasks list
  const [tasks, setTasks] = useState([]);
  // Form fields for creating a task
  const [newTask, setNewTask] = useState({ title: '', prompt: '', model: 'llama3', timeout_seconds: 120 });
  // Settings (RAM/CPU thresholds)
  const [settings, setSettings] = useState({ max_ram_percent: 85, max_cpu_percent: 90, breach_duration_seconds: 5 });

  // Load queue status periodically
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

  // Load tasks periodically
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

  // Load settings once
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

  // Handlers
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
    // refresh tasks
    const data = await getTasks();
    setTasks(data);
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    if (!newTask.title || !newTask.prompt) return;
    await createTask(newTask);
    setNewTask({ title: '', prompt: '', model: 'llama3', timeout_seconds: 120 });
    const data = await getTasks();
    setTasks(data);
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

  // Simple inline styles
  const containerStyle = { display: 'flex', flexDirection: 'column', fontFamily: 'Arial, sans-serif', padding: '10px' };
  const topBarStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', border: '1px solid #ccc', padding: '5px' };
  const mainStyle = { display: 'flex', flexGrow: 1 };
  const columnStyle = { flex: 1, margin: '5px', border: '1px solid #ddd', padding: '5px' };
  const footerStyle = { marginTop: '10px', borderTop: '1px solid #ccc', paddingTop: '10px' };

  return (
    <div style={containerStyle}>
      {/* Top Bar */}
      <div style={topBarStyle}>
        <div>
          <strong>Queue:</strong>{' '}{queue.queue_paused ? 'Paused' : 'Running'} &nbsp;|{' '}
          <strong>Pending:</strong> {queue.pending_count} {' '}|{' '}
          <strong>Running:</strong> {queue.running_count}
        </div>
        <div>
          {queue.queue_paused ? (
            <button onClick={handleResume}>Resume</button>
          ) : (
            <button onClick={handlePause}>Pause</button>
          )}
          <button onClick={handleClearFailed} style={{ marginLeft: '5px' }}>Clear Failed</button>
        </div>
      </div>
      {/* Main area */}
      <div style={mainStyle}>
        {/* Left – Create Task */}
        <div style={columnStyle}>
          <h3>Create Task</h3>
          <form onSubmit={handleCreateTask}>
            <div>
              <label>Title:<br />
                <input type="text" value={newTask.title} onChange={(e) => setNewTask({ ...newTask, title: e.target.value })} required />
              </label>
            </div>
            <div>
              <label>Prompt:<br />
                <textarea value={newTask.prompt} onChange={(e) => setNewTask({ ...newTask, prompt: e.target.value })} required rows={4} />
              </label>
            </div>
            <div>
              <label>Model:<br />
                <input type="text" value={newTask.model} onChange={(e) => setNewTask({ ...newTask, model: e.target.value })} />
              </label>
            </div>
            <div>
              <label>Timeout (s):<br />
                <input type="number" value={newTask.timeout_seconds} onChange={(e) => setNewTask({ ...newTask, timeout_seconds: Number(e.target.value) })} min={1} />
              </label>
            </div>
            <button type="submit" style={{ marginTop: '5px' }}>Create</button>
          </form>
        </div>
        {/* Right – Task List */}
        <div style={columnStyle}>
          <h3>Tasks</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ border: '1px solid #bbb' }}>Title</th>
                <th style={{ border: '1px solid #bbb' }}>Status</th>
                <th style={{ border: '1px solid #bbb' }}>Attempts</th>
                <th style={{ border: '1px solid #bbb' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id}>
                  <td style={{ border: '1px solid #bbb', padding: '2px' }}>{t.title}</td>
                  <td style={{ border: '1px solid #bbb', padding: '2px' }}>{t.status}</td>
                  <td style={{ border: '1px solid #bbb', padding: '2px' }}>{t.attempt_count}</td>
                  <td style={{ border: '1px solid #bbb', padding: '2px' }}>
                    {t.status === 'pending' && (
                      <button onClick={() => handleCancel(t.id)}>Cancel</button>
                    )}
                    {t.status === 'failed' && (
                      <button onClick={() => handleRetry(t.id)}>Retry</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {/* Settings panel */}
      <div style={footerStyle}>
        <h4>Settings (thresholds)</h4>
        <div>
          <label>Max RAM %:
            <input type="number" name="max_ram_percent" value={settings.max_ram_percent} onChange={handleSettingsChange} min={0} max={100} />
          </label>
          <label style={{ marginLeft: '10px' }}>Max CPU %:
            <input type="number" name="max_cpu_percent" value={settings.max_cpu_percent} onChange={handleSettingsChange} min={0} max={100} />
          </label>
          <label style={{ marginLeft: '10px' }}>Breach Duration (s):
            <input type="number" name="breach_duration_seconds" value={settings.breach_duration_seconds} onChange={handleSettingsChange} min={1} max={60} />
          </label>
          <button onClick={handleSettingsSave} style={{ marginLeft: '10px' }}>Save</button>
        </div>
      </div>
    </div>
  );
}
