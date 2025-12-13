import React, { useState } from 'react';

export const ComprehendPage = () => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [sentiment, setSentiment] = useState(null);

  const analyzeSentiment = async () => {
    if (!text.trim()) return;
    
    setLoading(true);
    // TODO: Implement sentiment analysis with Comprehend
    // Send text to backend /api/analyze-sentiment endpoint
    
    setLoading(false);
  };

  return (
    <div className="container" style={{ maxWidth: '896px' }}>
      <div className="card">
        <h2 style={{ fontSize: '30px', fontWeight: 'bold', color: '#111827', marginBottom: '24px' }}>Amazon Comprehend Sentiment Analysis</h2>
        <p style={{ color: '#4b5563', marginBottom: '32px' }}>
          Analyze the sentiment of your text to understand if it's positive, negative, neutral, or mixed.
        </p>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '8px' }}>
            Enter text to analyze
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type or paste your text here..."
            className="text-input"
            rows="6"
          />
        </div>

        <div style={{ marginBottom: '24px' }}>
          <button
            onClick={analyzeSentiment}
            disabled={loading || !text.trim()}
            className="btn-primary"
          >
            {loading ? 'Analyzing...' : 'Analyze Sentiment'}
          </button>
        </div>

        {sentiment && (
          <div className="card" style={{ backgroundColor: '#faf5ff' }}>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '16px' }}>Sentiment Results</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <div className="flex justify-between mb-1">
                  <span style={{ fontSize: '14px', fontWeight: '500', color: '#374151' }}>Overall Sentiment</span>
                  <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#7c3aed' }}>{sentiment.sentiment}</span>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span style={{ fontSize: '14px', fontWeight: '500', color: '#374151' }}>Positive</span>
                  <span style={{ fontSize: '14px', color: '#4b5563' }}>{((sentiment.scores?.positive || 0) * 100).toFixed(1)}%</span>
                </div>
                <div style={{ width: '100%', backgroundColor: '#e5e7eb', borderRadius: '9999px', height: '8px' }}>
                  <div
                    style={{
                      backgroundColor: '#22c55e',
                      height: '8px',
                      borderRadius: '9999px',
                      width: `${((sentiment.scores?.positive || 0) * 100)}%`
                    }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span style={{ fontSize: '14px', fontWeight: '500', color: '#374151' }}>Negative</span>
                  <span style={{ fontSize: '14px', color: '#4b5563' }}>{((sentiment.scores?.negative || 0) * 100).toFixed(1)}%</span>
                </div>
                <div style={{ width: '100%', backgroundColor: '#e5e7eb', borderRadius: '9999px', height: '8px' }}>
                  <div
                    style={{
                      backgroundColor: '#ef4444',
                      height: '8px',
                      borderRadius: '9999px',
                      width: `${((sentiment.scores?.negative || 0) * 100)}%`
                    }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span style={{ fontSize: '14px', fontWeight: '500', color: '#374151' }}>Neutral</span>
                  <span style={{ fontSize: '14px', color: '#4b5563' }}>{((sentiment.scores?.neutral || 0) * 100).toFixed(1)}%</span>
                </div>
                <div style={{ width: '100%', backgroundColor: '#e5e7eb', borderRadius: '9999px', height: '8px' }}>
                  <div
                    style={{
                      backgroundColor: '#6b7280',
                      height: '8px',
                      borderRadius: '9999px',
                      width: `${((sentiment.scores?.neutral || 0) * 100)}%`
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div style={{ marginTop: '24px', padding: '16px', backgroundColor: '#faf5ff', borderRadius: '12px' }}>
          <p style={{ fontSize: '14px', color: '#6b21a8' }}>
            <strong>Note:</strong> This is a placeholder. Implement the Comprehend integration by connecting to your backend API endpoint.
          </p>
        </div>
      </div>
    </div>
  );
};
