import { useState, useRef, useEffect } from 'react';
import './AIdeaChat.css';

const API_ENDPOINT = '/api/ai-idea';

export default function AIdeaChat({ onTasksCreated }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'assistant',
      content: "Hey! I'm your AI task planner. Tell me what you want to accomplish, and I'll break it down into tasks for OneQueue.\n\nFor example:\n• \"I need to process 100 PDFs and summarize each one\"\n• \"Scrape news from 5 websites and analyze sentiment\"\n• \"Generate images for all my blog posts this month\"",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [taskPlan, setTaskPlan] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);

    try {
      // Send to AI planner
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      });

      if (!response.ok) throw new Error('Failed to process idea');

      const data = await response.json();

      // Add AI response
      const aiMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: data.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, aiMessage]);

      // If AI generated a task plan, show it
      if (data.taskPlan) {
        setTaskPlan(data.taskPlan);
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}`,
        isError: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
      inputRef.current?.focus();
    }
  };

  const handleApprovePlan = async () => {
    if (!taskPlan) return;

    try {
      const response = await fetch('/api/tasks/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tasks: taskPlan.tasks.map(t => ({
            title: t.title,
            prompt: t.prompt,
            model: t.model,
            priority: t.priority
          }))
        })
      });

      if (!response.ok) throw new Error('Failed to create tasks');

      // Success!
      const successMessage = {
        id: Date.now(),
        type: 'system',
        content: `✅ Created ${taskPlan.tasks.length} tasks successfully!`,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, successMessage]);
      setTaskPlan(null);
      
      // Notify parent to refresh task list
      onTasksCreated?.();
      
      // Clear conversation
      setMessages([{
        id: Date.now() + 1,
        type: 'assistant',
        content: "Tasks created! What's next on your mind?",
        timestamp: new Date()
      }]);
    } catch (error) {
      const errorMessage = {
        id: Date.now(),
        type: 'assistant',
        content: `Failed to create tasks: ${error.message}`,
        isError: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleRejectPlan = () => {
    setTaskPlan(null);
    const message = {
      id: Date.now(),
      type: 'assistant',
      content: "No problem! Tell me what you'd like to change, or give me a new idea.",
      timestamp: new Date()
    };
    setMessages(prev => [...prev, message]);
  };

  return (
    <div className="aidea-chat">
      <div className="chat-header">
        <h2>💡 AI Idea Planner</h2>
        <p>Describe your idea, I'll create the tasks</p>
      </div>

      <div className="chat-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.type} ${message.isError ? 'error' : ''}`}
          >
            <div className="message-content">
              {message.type === 'assistant' && (
                <div className="message-avatar">🤖</div>
              )}
              {message.type === 'user' && (
                <div className="message-avatar">👤</div>
              )}
              {message.type === 'system' && (
                <div className="message-avatar">✅</div>
              )}
              <div className="message-text">{message.content}</div>
            </div>
            <div className="message-timestamp">
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ))}
        {isProcessing && (
          <div className="message assistant">
            <div className="message-content">
              <div className="message-avatar">🤖</div>
              <div className="message-text">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {taskPlan && (
        <div className="task-plan-preview">
          <div className="plan-header">
            <h3>📋 Proposed Task Plan</h3>
            <div className="plan-actions">
              <button
                onClick={handleRejectPlan}
                className="btn btn-secondary"
              >
                ✏️ Modify
              </button>
              <button
                onClick={handleApprovePlan}
                className="btn btn-primary"
                disabled={isProcessing}
              >
                ✅ Approve & Create Tasks
              </button>
            </div>
          </div>
          <div className="plan-tasks">
            {taskPlan.tasks.map((task, index) => (
              <div key={index} className="plan-task-item">
                <div className="task-number">{index + 1}</div>
                <div className="task-details">
                  <div className="task-title">{task.title}</div>
                  <div className="task-prompt">{task.prompt}</div>
                  <div className="task-meta">
                    <span className="task-model">🤖 {task.model}</span>
                    <span className="task-priority">Priority: {task.priority}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe your idea... (e.g., 'I want to analyze sentiment of 1000 tweets and create a report')"
          rows={3}
          disabled={isProcessing}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
        />
        <button
          type="submit"
          disabled={isProcessing || !input.trim()}
          className="btn btn-primary"
        >
          {isProcessing ? 'Processing...' : 'Send 💡'}
        </button>
      </form>
    </div>
  );
}
