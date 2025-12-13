import React, { useState } from 'react';

export const RekognitionPage = () => {
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const analyzeImage = async () => {
    if (!imageFile) return;
    
    setLoading(true);
    // TODO: Implement image analysis with Rekognition
    // Send image to backend /api/analyze-image endpoint
    
    setLoading(false);
  };

  return (
    <div className="container" style={{ maxWidth: '896px' }}>
      <div className="card">
        <h2 style={{ fontSize: '30px', fontWeight: 'bold', color: '#111827', marginBottom: '24px' }}>Amazon Rekognition Image Analysis</h2>
        <p style={{ color: '#4b5563', marginBottom: '32px' }}>
          Upload an image to detect objects, faces, text, and other features using Amazon Rekognition.
        </p>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151', marginBottom: '8px' }}>
            Upload Image
          </label>
          <div className="file-upload-area" onClick={() => document.getElementById('image-upload').click()}>
            <input
              id="image-upload"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="hidden"
            />
            {imagePreview ? (
              <div>
                <img src={imagePreview} alt="Preview" style={{ maxWidth: '100%', maxHeight: '256px', margin: '0 auto', borderRadius: '8px', marginBottom: '16px', display: 'block' }} />
                <p style={{ fontSize: '14px', color: '#4b5563' }}>Click to change image</p>
              </div>
            ) : (
              <div>
                <svg style={{ width: '48px', height: '48px', color: '#60a5fa', margin: '0 auto 16px', display: 'block' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <p style={{ color: '#4b5563' }}>Click to upload an image</p>
                <p style={{ fontSize: '14px', color: '#9ca3af', marginTop: '8px' }}>PNG, JPG, GIF up to 10MB</p>
              </div>
            )}
          </div>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <button
            onClick={analyzeImage}
            disabled={loading || !imageFile}
            className="btn-primary"
          >
            {loading ? 'Analyzing...' : 'Analyze Image'}
          </button>
        </div>

        {results && (
          <div className="card" style={{ backgroundColor: '#fff7ed' }}>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '16px' }}>Analysis Results</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {results.labels && results.labels.length > 0 && (
                <div>
                  <h4 style={{ fontWeight: '600', color: '#374151', marginBottom: '8px' }}>Detected Labels:</h4>
                  <div className="flex flex-wrap gap-2">
                    {results.labels.map((label, index) => (
                      <span key={index} style={{
                        padding: '4px 12px',
                        backgroundColor: '#fed7aa',
                        color: '#9a3412',
                        borderRadius: '9999px',
                        fontSize: '14px'
                      }}>
                        {label.Name} ({label.Confidence.toFixed(1)}%)
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {results.faces && results.faces.length > 0 && (
                <div>
                  <h4 style={{ fontWeight: '600', color: '#374151', marginBottom: '8px' }}>Detected Faces: {results.faces.length}</h4>
                </div>
              )}
              {results.text && results.text.length > 0 && (
                <div>
                  <h4 style={{ fontWeight: '600', color: '#374151', marginBottom: '8px' }}>Detected Text:</h4>
                  <p style={{ color: '#4b5563' }}>{results.text.join(', ')}</p>
                </div>
              )}
            </div>
          </div>
        )}

        <div style={{ marginTop: '24px', padding: '16px', backgroundColor: '#fff7ed', borderRadius: '12px' }}>
          <p style={{ fontSize: '14px', color: '#9a3412' }}>
            <strong>Note:</strong> This is a placeholder. Implement the Rekognition integration by connecting to your backend API endpoint.
          </p>
        </div>
      </div>
    </div>
  );
};
