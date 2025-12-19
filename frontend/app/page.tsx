'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, BarChart3, Loader2, AlertCircle, CheckCircle, Code2, ImageIcon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  visualization?: string;
  codeExecuted?: string;
  visualizationCode?: string;
  timestamp: Date;
  isError?: boolean;
}

export default function DataAnalyticsAgent() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m your NYC 311 Data Analytics Agent powered by AI. I have full context of the dataset and can write custom Python/pandas code to answer your questions.\n\n💡 Tip: Charts are created only when relevant or explicitly requested!',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [showCode, setShowCode] = useState<{[key: number]: boolean}>({});
  const [showVizCode, setShowVizCode] = useState<{[key: number]: boolean}>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    checkBackendStatus();
    const interval = setInterval(checkBackendStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkBackendStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      if (response.ok) {
        const data = await response.json();
        setBackendStatus(data.dataset_loaded ? 'connected' : 'disconnected');
      } else {
        setBackendStatus('disconnected');
      }
    } catch (error) {
      setBackendStatus('disconnected');
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: currentInput }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response from backend');
      }

      const data = await response.json();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response,
        visualization: data.visualization,
        codeExecuted: data.code_executed,
        visualizationCode: data.visualization_code,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}. Make sure the FastAPI backend is running on http://localhost:8000`,
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleCode = (index: number) => {
    setShowCode(prev => ({...prev, [index]: !prev[index]}));
  };

  const toggleVizCode = (index: number) => {
    setShowVizCode(prev => ({...prev, [index]: !prev[index]}));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      <div className="max-w-7xl mx-auto p-4 h-screen flex flex-col">
        {/* Header */}
        <div className="bg-white/10 backdrop-blur-lg rounded-t-2xl border border-white/20 p-6 shadow-2xl">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-3 rounded-xl shadow-lg">
                <BarChart3 className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white">NYC 311 Analytics Agent</h1>
                <p className="text-blue-200 text-sm">AI-Powered Analysis • Smart Visualizations • View All Code</p>
              </div>
            </div>
            <div className="flex items-center gap-3 bg-black/30 px-4 py-2 rounded-lg">
              <div className={`w-3 h-3 rounded-full ${
                backendStatus === 'connected' ? 'bg-green-400' : 
                backendStatus === 'disconnected' ? 'bg-red-400' : 
                'bg-yellow-400'
              } animate-pulse`}></div>
              <span className="text-white text-sm font-medium">
                {backendStatus === 'connected' ? '✓ Connected' : 
                 backendStatus === 'disconnected' ? '✗ Backend Offline' : 
                 '⟳ Checking...'}
              </span>
            </div>
          </div>
        </div>

        {/* Messages Container */}
        <div className="flex-1 bg-white/5 backdrop-blur-lg border-x border-white/20 overflow-y-auto p-6 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-4xl rounded-2xl p-5 shadow-lg ${
                  message.role === 'user'
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white'
                    : message.isError
                    ? 'bg-red-500/20 text-red-100 border border-red-500/50'
                    : 'bg-white/10 text-white border border-white/20'
                }`}
              >
                {message.isError && (
                  <div className="flex items-center gap-2 mb-3 pb-3 border-b border-red-400/30">
                    <AlertCircle className="w-5 h-5" />
                    <span className="font-semibold">Error</span>
                  </div>
                )}
                
                <div className="prose prose-invert max-w-none leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                </div>
                
                {/* Analysis Code Section */}
                {message.codeExecuted && message.role === 'assistant' && (
                  <div className="mt-4">
                    <button
                      onClick={() => toggleCode(index)}
                      className="flex items-center gap-2 px-3 py-2 bg-blue-500/20 hover:bg-blue-500/30 rounded-lg text-sm text-blue-200 transition-colors border border-blue-400/30"
                    >
                      <Code2 className="w-4 h-4" />
                      {showCode[index] ? 'Hide' : 'Show'} analysis code
                    </button>
                    
                    {showCode[index] && (
                      <div className="mt-3">
                        <div className="text-xs text-blue-300 mb-2 font-semibold">📊 Pandas Analysis Code:</div>
                        <pre className="p-4 bg-black/60 rounded-lg text-xs overflow-x-auto border border-white/10 font-mono">
                          <code className="text-green-300">{message.codeExecuted}</code>
                        </pre>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Visualization */}
                {message.visualization && (
                  <div className="mt-4">
                    <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                      <div className="flex items-center gap-2 mb-3">
                        <ImageIcon className="w-4 h-4 text-purple-300" />
                        <span className="text-sm font-semibold text-purple-300">Generated Visualization</span>
                      </div>
                      <img 
                        src={`data:image/png;base64,${message.visualization}`} 
                        alt="Data Visualization" 
                        className="w-full rounded-lg shadow-lg"
                      />
                      
                      {/* Visualization Code */}
                      {message.visualizationCode && (
                        <div className="mt-3">
                          <button
                            onClick={() => toggleVizCode(index)}
                            className="flex items-center gap-2 px-3 py-2 bg-purple-500/20 hover:bg-purple-500/30 rounded-lg text-sm text-purple-200 transition-colors border border-purple-400/30"
                          >
                            <Code2 className="w-4 h-4" />
                            {showVizCode[index] ? 'Hide' : 'Show'} visualization code
                          </button>
                          
                          {showVizCode[index] && (
                            <div className="mt-3">
                              <div className="text-xs text-purple-300 mb-2 font-semibold">📈 Matplotlib/Seaborn Code:</div>
                              <pre className="p-4 bg-black/60 rounded-lg text-xs overflow-x-auto border border-white/10 font-mono">
                                <code className="text-pink-300">{message.visualizationCode}</code>
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                <div className="text-xs opacity-60 mt-3 flex items-center gap-2">
                  {message.role === 'assistant' && !message.isError && (
                    <CheckCircle className="w-3 h-3" />
                  )}
                  {message.timestamp.toLocaleTimeString('en-US', { hour12: false })}
                </div>
              </div>
            </div>
          ))}
          
          {/* Loading State */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/10 text-white rounded-2xl p-5 shadow-lg border border-white/20">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <div>
                    <div className="font-medium">Analyzing your query...</div>
                    <div className="text-xs opacity-70 mt-1">
                      AI is writing custom code • Deciding on visualization
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <div className="bg-white/10 backdrop-blur-lg rounded-b-2xl border border-white/20 p-6 shadow-2xl">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask anything... Try: 'Show me a chart of top 10 complaint types'"
              className="flex-1 px-6 py-4 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              disabled={isLoading || backendStatus !== 'connected'}
            />
            <button
              onClick={handleSubmit}
              disabled={isLoading || !input.trim() || backendStatus !== 'connected'}
              className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white rounded-xl font-semibold flex items-center gap-2 transition-all shadow-lg hover:shadow-xl hover:scale-105"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span className="hidden sm:inline">Analyzing</span>
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span className="hidden sm:inline">Send</span>
                </>
              )}
            </button>
          </div>
          
          <div className="mt-3 flex items-center gap-4 text-xs text-white/60">
            <span className="flex items-center gap-1">
              <Code2 className="w-3 h-3" />
              View all generated code
            </span>
            <span className="flex items-center gap-1">
              <ImageIcon className="w-3 h-3" />
              Charts only when relevant
            </span>
          </div>
          
          {backendStatus !== 'connected' && (
            <div className="mt-4 p-4 bg-yellow-500/20 border border-yellow-500/50 rounded-lg">
              <p className="text-yellow-200 text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                <span>
                  Backend not connected. Please ensure:
                  <br />
                  1. Python backend is running (python app.py)
                  <br />
                  2. CSV file is in the backend directory
                  <br />
                  3. All dependencies are installed
                </span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}