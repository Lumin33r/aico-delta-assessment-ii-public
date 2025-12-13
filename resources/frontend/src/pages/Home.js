import React from 'react';
import { Link } from 'react-router-dom';

export const Home = () => {
  return (
    <div className="container">
      <div className="text-center mb-6" style={{ marginBottom: '64px' }}>
        <h1 style={{
          fontSize: '48px',
          fontWeight: 'bold',
          background: 'linear-gradient(to right, #2563eb, #1e40af)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          marginBottom: '24px'
        }}>
          AWS AI Services Dashboard
        </h1>
        <p style={{ fontSize: '20px', color: '#4b5563', maxWidth: '672px', margin: '0 auto' }}>
          Harness the power of AWS AI services through an intuitive interface
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '32px',
        marginBottom: '80px'
      }}>
        <Link to="/lex" className="service-card">
          <div className="text-center">
            <div style={{
              width: '64px',
              height: '64px',
              background: 'linear-gradient(to bottom right, #3b82f6, #2563eb)',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
              transition: 'transform 0.3s'
            }}>
              <svg style={{ width: '32px', height: '32px', color: 'white' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '12px' }}>
              Amazon Lex
            </h3>
            <p style={{ color: '#4b5563', lineHeight: '1.625' }}>
              Build conversational interfaces using voice and text
            </p>
          </div>
        </Link>

        <Link to="/polly" className="service-card">
          <div className="text-center">
            <div style={{
              width: '64px',
              height: '64px',
              background: 'linear-gradient(to bottom right, #22c55e, #16a34a)',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
              transition: 'transform 0.3s'
            }}>
              <svg style={{ width: '32px', height: '32px', color: 'white' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M9 12a1 1 0 00-1-1H4a1 1 0 00-1 1v4a1 1 0 001 1h4l5 5V7l-5 5z" />
              </svg>
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '12px' }}>
              Amazon Polly
            </h3>
            <p style={{ color: '#4b5563', lineHeight: '1.625' }}>
              Convert text to natural-sounding speech using neural voice technology
            </p>
          </div>
        </Link>

        <Link to="/comprehend" className="service-card">
          <div className="text-center">
            <div style={{
              width: '64px',
              height: '64px',
              background: 'linear-gradient(to bottom right, #a855f7, #9333ea)',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
              transition: 'transform 0.3s'
            }}>
              <svg style={{ width: '32px', height: '32px', color: 'white' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '12px' }}>
              Amazon Comprehend
            </h3>
            <p style={{ color: '#4b5563', lineHeight: '1.625' }}>
              Discover insights and relationships in text using natural language processing
            </p>
          </div>
        </Link>

        <Link to="/rekognition" className="service-card">
          <div className="text-center">
            <div style={{
              width: '64px',
              height: '64px',
              background: 'linear-gradient(to bottom right, #f97316, #ea580c)',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
              transition: 'transform 0.3s'
            }}>
              <svg style={{ width: '32px', height: '32px', color: 'white' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '12px' }}>
              Amazon Rekognition
            </h3>
            <p style={{ color: '#4b5563', lineHeight: '1.625' }}>
              Analyze images and videos to detect objects, faces, and text
            </p>
          </div>
        </Link>
      </div>

      <div className="text-center" style={{ marginTop: '80px' }}>
        <div className="card" style={{ maxWidth: '672px', margin: '0 auto' }}>
          <h3 style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', marginBottom: '16px' }}>Get Started</h3>
          <p style={{ color: '#4b5563', marginBottom: '24px', lineHeight: '1.625' }}>
            Explore AWS AI services through our interactive dashboard. Try out Lex for chatbots, Polly for text-to-speech, Comprehend for sentiment analysis, or Rekognition for image analysis.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link to="/lex" className="btn-primary" style={{ textDecoration: 'none', display: 'inline-block' }}>
              Try Lex
            </Link>
            <Link to="/polly" className="btn-success" style={{ textDecoration: 'none', display: 'inline-block' }}>
              Try Polly
            </Link>
            <Link to="/comprehend" className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-block' }}>
              Try Comprehend
            </Link>
            <Link to="/rekognition" className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-block' }}>
              Try Rekognition
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
