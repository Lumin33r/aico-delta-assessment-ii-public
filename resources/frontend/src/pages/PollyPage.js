import React, { useState } from 'react';

export const PollyPage = () => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);

  const convertToSpeech = async () => {
    if (!text.trim()) return;
    
    setLoading(true);
    // TODO: Implement text-to-speech with Polly
    // Send text to backend /api/text-to-speech endpoint
    
    setLoading(false);
  };

  return (
    <div className="container" style={{ maxWidth: '896px' }}>
      <div className="card">
        <h2 style={{ fontSize: '30px', fontWeight: 'bold', color: '#111827', marginBottom: '24px' }}>Amazon Polly Text-to-Speech</h2>
        <p style={{ color: '#4b5563', marginBottom: '32px' }}>
          Convert your text into natural-sounding speech using Amazon Polly.
        </p>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '8px' }}>
            Enter text to convert
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
            onClick={convertToSpeech}
            disabled={loading || !text.trim()}
            className="btn-success"
          >
            {loading ? 'Converting...' : 'Convert to Speech'}
          </button>
        </div>

        {audioUrl && (
          <div className="audio-player">
            <p style={{ fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '8px' }}>Generated Audio:</p>
            <audio controls src={audioUrl} style={{ width: '100%' }}>
              Your browser does not support the audio element.
            </audio>
          </div>
        )}

        <div style={{ marginTop: '24px', padding: '16px', backgroundColor: '#f0fdf4', borderRadius: '12px' }}>
          <p style={{ fontSize: '14px', color: '#166534' }}>
            <strong>Note:</strong> This is a placeholder. Implement the Polly integration by connecting to your backend API endpoint.
          </p>
        </div>
      </div>
    </div>
  );
};
