import { useState, useEffect } from 'react';
import { getAllModels, getSmartRoute } from './api';

// Top 10 recommended models from benchmark tests
const TOP_MODELS = [
  { id: "meta/llama-4-maverick-17b-128e-instruct", name: "🏆 Llama 4 Maverick (Best Overall)", tier: "flagship", badge: "BEST" },
  { id: "qwen/qwen2.5-coder-32b-instruct", name: "💻 Qwen Coder 32B (Best Code)", tier: "coding", badge: "BEST FOR CODE" },
  { id: "deepseek-ai/deepseek-r1-distill-llama-8b", name: "🧠 DeepSeek R1 (Best Reasoning)", tier: "reasoning", badge: "BEST FOR REASONING" },
  { id: "microsoft/phi-3.5-vision-instruct", name: "👁️ Phi-3.5 Vision (Multimodal)", tier: "multimodal", badge: "FAST" },
  { id: "microsoft/phi-3-mini-4k-instruct", name: "⚡ Phi-3 Mini (Fastest)", tier: "fast", badge: "FASTEST" },
  { id: "meta/llama-3.1-70b-instruct", name: "🦙 Llama 3.1 70B (High Quality)", tier: "flagship", badge: "HIGH QUALITY" },
  { id: "meta/llama-3.1-405b-instruct", name: "🚀 Llama 3.1 405B (405B Params)", tier: "flagship", badge: "MAX QUALITY" },
  { id: "mistralai/mistral-7b-instruct", name: "🌍 Mistral 7B (Multilingual)", tier: "fast", badge: "MULTILINGUAL" },
  { id: "qwen/qwen3-next-80b-a3b-instruct", name: "⚡ Qwen 3 Next 80B", tier: "flagship", badge: "ADVANCED" },
  { id: "google/gemma-3-27b-it", name: "🔮 Gemma 3 27B (Balanced)", tier: "flagship", badge: "BALANCED" },
];

const TOP_MODEL_IDS = TOP_MODELS.map(m => m.id);

export default function ModelSelector({
  value,
  onChange,
  prompt = '',
  showRecommendation = true,
  showAutoOption = true
}) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recommendation, setRecommendation] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    if (showRecommendation && value === 'auto' && prompt.length > 10) {
      getSmartRouting();
    }
  }, [prompt, value, showRecommendation]);

  const fetchModels = async () => {
    try {
      setLoading(true);
      const data = await getAllModels();

      // Group models by provider
      const nvidiaModels = data.data.filter(m => m.id.includes('/') && m.owned_by !== 'local');
      const ollamaModels = data.data.filter(m => m.owned_by === 'local' || !m.id.includes('/'));

      // Separate top recommended models from others
      const topRecommended = nvidiaModels.filter(m => TOP_MODEL_IDS.includes(m.id));
      const otherModels = nvidiaModels.filter(m => !TOP_MODEL_IDS.includes(m.id));

      setModels([
        { group: 'Smart Routing', models: [{ id: 'auto', name: 'Auto-select best model', tier: 'smart' }] },
        { group: '⭐ Top Recommended (Tested & Optimized)', models: TOP_MODELS.filter(tm => 
          nvidiaModels.some(nm => nm.id === tm.id)
        ) },
        { group: 'Other NVIDIA Models', models: otherModels.slice(0, 15) },
        { group: 'Ollama Local', models: ollamaModels }
      ]);
    } catch (err) {
      setError('Failed to load models: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getSmartRouting = async () => {
    try {
      const data = await getSmartRoute(prompt);
      setRecommendation(data);
    } catch (err) {
      console.error('Smart routing failed:', err);
    }
  };

  if (loading) {
    return (
      <div className="model-selector loading">
        <span>Loading models...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="model-selector error">
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div className="model-selector">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="model-dropdown"
        aria-label="Select model"
      >
        {models.map(group => (
          <optgroup 
            key={group.group} 
            label={group.group}
            labelClassName={group.group.includes('Top Recommended') ? 'recommended' : ''}
          >
            {group.models.map(model => {
              // Check if this is a top recommended model
              const topModel = TOP_MODELS.find(tm => tm.id === model.id);
              const displayName = topModel ? topModel.name : (model.name || model.id.split('/').pop());
              const badge = topModel?.badge ? `[${topModel.badge}]` : '';
              
              return (
                <option
                  key={model.id}
                  value={model.id}
                  disabled={model.tier === 'smart' && !showAutoOption}
                  className={topModel ? 'top-model' : ''}
                >
                  {displayName} {badge ? ` ${badge}` : ''}
                </option>
              );
            })}
          </optgroup>
        ))}
      </select>

      {showRecommendation && value === 'auto' && recommendation && prompt.length > 10 && (
        <div className="recommendation-banner" role="status">
          <div className="recommendation-icon" aria-hidden="true">🎯</div>
          <div className="recommendation-content">
            <div className="recommendation-label">Recommended:</div>
            <div className="recommendation-model">
              {recommendation.recommended_model.split('/').pop()}
            </div>
            <div className="recommendation-reason">
              {recommendation.task_type} task • {recommendation.model_info?.quality_score}/10 quality
            </div>
          </div>
        </div>
      )}

      {value !== 'auto' && (
        <div className="model-info">
          <small className="model-hint">
            {value.includes('/') ? '☁️ Cloud model' : '💻 Local model'}
            {TOP_MODEL_IDS.includes(value) && ' • Top Recommended'}
          </small>
        </div>
      )}
    </div>
  );
}
