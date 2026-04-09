import { useState } from 'react';
import HealthDashboard from './HealthDashboard';
import ModelSelector from './ModelSelector';

export default function TestComponents() {
  const [selectedModel, setSelectedModel] = useState('auto');
  const [prompt, setPrompt] = useState('Write a Python function to calculate fibonacci numbers');

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>🧪 Component Test</h1>
      
      <section style={{ marginBottom: '2rem' }}>
        <h2>Health Dashboard</h2>
        <HealthDashboard />
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h2>Model Selector</h2>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
            Test Prompt:
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', minHeight: '80px' }}
            placeholder="Enter a prompt to test smart routing..."
          />
        </div>
        <ModelSelector
          value={selectedModel}
          onChange={setSelectedModel}
          prompt={prompt}
          showRecommendation={true}
        />
        <div style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#666' }}>
          Selected: <strong>{selectedModel}</strong>
        </div>
      </section>

      <section>
        <h2>API Test</h2>
        <button
          onClick={async () => {
            const res = await fetch('http://localhost:8081/router/route', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ prompt })
            });
            const data = await res.json();
            alert(JSON.stringify(data, null, 2));
          }}
          style={{
            padding: '0.75rem 1.5rem',
            background: '#4f46e5',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: '600'
          }}
        >
          Test Smart Routing
        </button>
      </section>
    </div>
  );
}
