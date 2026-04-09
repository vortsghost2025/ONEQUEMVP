import { useState, useEffect } from 'react';
import { getSystemHealth } from './api';

export default function HealthDashboard() {
  const [health, setHealth] = useState({
    backend: 'unknown',
    ollama: 'unknown',
    nvidia_api: 'unknown'
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10s
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const data = await getSystemHealth();
      setHealth(data);
      setLoading(false);
    } catch (err) {
      console.error('Health check failed:', err);
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    if (status === 'healthy' || status === 'configured') return '✅';
    if (status === 'offline' || status === 'error') return '❌';
    return '⚠️';
  };

  const getStatusColor = (status) => {
    if (status === 'healthy' || status === 'configured') return 'status-healthy';
    if (status === 'offline' || status === 'error') return 'status-error';
    return 'status-warning';
  };

  const getStatusLabel = (key, status) => {
    const labels = {
      backend: 'Backend API',
      ollama: 'Ollama (Local)',
      nvidia_api: 'NVIDIA Cloud'
    };
    
    const statusText = {
      healthy: 'Healthy',
      configured: 'Configured',
      offline: 'Offline',
      error: 'Error',
      unknown: 'Checking...'
    };

    return `${labels[key]}: ${statusText[status] || status}`;
  };

  return (
    <div className="health-dashboard" role="region" aria-label="System Health">
      <div className="health-header">
        <h3>System Health</h3>
        {!loading && (
          <span className="health-timestamp">
            Updated {new Date().toLocaleTimeString()}
          </span>
        )}
      </div>

      <div className="health-grid">
        {Object.entries(health).map(([key, status]) => (
          <div 
            key={key}
            className={`health-card ${getStatusColor(status)}`}
            role="status"
            aria-label={getStatusLabel(key, status)}
          >
            <div className="health-icon" aria-hidden="true">
              {getStatusIcon(status)}
            </div>
            <div className="health-info">
              <div className="health-service">
                {key === 'backend' && 'Backend'}
                {key === 'ollama' && 'Ollama'}
                {key === 'nvidia_api' && 'NVIDIA'}
              </div>
              <div className="health-status">{status}</div>
            </div>
          </div>
        ))}
      </div>

      {health.nvidia_key_loaded && (
        <div className="nvidia-badge">
          <span className="badge-icon" aria-hidden="true">🚀</span>
          <span className="badge-text">189 NVIDIA models available</span>
        </div>
      )}
    </div>
  );
}
