import React, { useState } from 'react';
// TODO: Import service when ready
// import { chatWithBot } from '../services/aiServices';

export const LexPage = () => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!message.trim()) return;
    
    setLoading(true);
    // TODO: Implement chat with Lex bot
    // const response = await chatWithBot(message);
    // Add response to chatHistory
    
    setLoading(false);
  };

  return (
    <div className="container" style={{ maxWidth: '896px' }}>
      <div className="card">
        <h2 style={{ fontSize: '30px', fontWeight: 'bold', color: '#111827', marginBottom: '24px' }}>Amazon Lex Chatbot</h2>
        <p style={{ color: '#4b5563', marginBottom: '32px' }}>
          Interact with your Lex bot. Type a message below to start a conversation.
        </p>

        <div style={{ marginBottom: '24px' }}>
          <div style={{
            backgroundColor: '#f9fafb',
            borderRadius: '12px',
            padding: '24px',
            minHeight: '400px',
            maxHeight: '400px',
            overflowY: 'auto',
            marginBottom: '16px'
          }}>
            {chatHistory.length === 0 ? (
              <div className="text-center" style={{ color: '#9ca3af', marginTop: '80px' }}>
                <p>Start a conversation by sending a message below</p>
              </div>
            ) : (
              chatHistory.map((msg, index) => (
                <div
                  key={index}
                  style={{ marginBottom: '16px', textAlign: msg.role === 'user' ? 'right' : 'left' }}
                >
                  <div
                    style={{
                      display: 'inline-block',
                      padding: '12px',
                      borderRadius: '8px',
                      backgroundColor: msg.role === 'user' ? '#2563eb' : '#e5e7eb',
                      color: msg.role === 'user' ? 'white' : '#111827'
                    }}
                  >
                    {msg.content}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div style={{ textAlign: 'left' }}>
                <div style={{
                  display: 'inline-block',
                  backgroundColor: '#e5e7eb',
                  color: '#111827',
                  padding: '12px',
                  borderRadius: '8px'
                }}>
                  Thinking...
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type your message..."
              style={{
                flex: 1,
                padding: '12px 16px',
                border: '1px solid #d1d5db',
                borderRadius: '12px',
                outline: 'none',
                transition: 'all 0.3s'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#3b82f6';
                e.target.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.1)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#d1d5db';
                e.target.style.boxShadow = 'none';
              }}
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !message.trim()}
              className="btn-primary"
            >
              Send
            </button>
          </div>
        </div>

        <div style={{ marginTop: '24px', padding: '16px', backgroundColor: '#eff6ff', borderRadius: '12px' }}>
          <p style={{ fontSize: '14px', color: '#1e40af' }}>
            <strong>Note:</strong> This is a placeholder. Implement the Lex integration by connecting to your backend API endpoint.
          </p>
        </div>
      </div>
    </div>
  );
};
