import { useState, useEffect } from 'react';
import { getCuratedModels, generateNvidia } from './api';

export default function NvidiaTest() {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const data = await getCuratedModels();
      setModels(data.models);
      if (data.models.length > 0) {
        setSelectedModel(data.models[0].id);
      }
    } catch (err) {
      setError('Failed to fetch models: ' + err.message);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    setLoading(true);
    setError('');
    setResponse('');

    try {
      const data = await generateNvidia(selectedModel, prompt);
      setResponse(data.response);
    } catch (err) {
      setError('Generation failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="nvidia-test">
      <h2>🔧 NVIDIA API Test</h2>
      
      <div className="model-selector">
        <label>Model:</label>
        <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
          {models.map(m => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.tier})
            </option>
          ))}
        </select>
      </div>

      <div className="prompt-input">
        <label>Prompt:</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prompt..."
          rows={4}
        />
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading || !prompt.trim()}
        className="btn btn-primary"
      >
        {loading ? 'Generating...' : 'Generate'}
      </button>

      {error && <div className="error">{error}</div>}

      {response && (
        <div className="response">
          <h3>Response:</h3>
          <pre>{response}</pre>
        </div>
      )}
    </div>
  );
}
