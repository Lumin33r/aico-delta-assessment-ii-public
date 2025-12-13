import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export const Layout = ({ children }) => {
  const location = useLocation();

  const navigation = [
    { name: 'Home', href: '/', current: location.pathname === '/' },
    { name: 'Lex', href: '/lex', current: location.pathname === '/lex' },
    { name: 'Polly', href: '/polly', current: location.pathname === '/polly' },
    { name: 'Comprehend', href: '/comprehend', current: location.pathname === '/comprehend' },
    { name: 'Rekognition', href: '/rekognition', current: location.pathname === '/rekognition' },
  ];

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(to bottom right, #f8fafc, #e0f2fe)' }}>
      <nav style={{ backgroundColor: 'rgba(255, 255, 255, 0.8)', backdropFilter: 'blur(10px)', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}>
        <div className="container">
          <div className="flex justify-between" style={{ height: '80px' }}>
            <div className="flex">
              <div className="flex items-center">
                <div className="flex items-center" style={{ gap: '12px' }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    background: 'linear-gradient(to bottom right, #2563eb, #1d4ed8)',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'transform 0.3s',
                    cursor: 'pointer'
                  }}>
                    <svg style={{ width: '24px', height: '24px', color: 'white' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <h1 style={{
                    fontSize: '24px',
                    fontWeight: 'bold',
                    background: 'linear-gradient(to right, #2563eb, #1e40af)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text'
                  }}>
                    AWS AI Services
                  </h1>
                </div>
              </div>
              <div className="flex items-center" style={{ marginLeft: '40px', gap: '8px' }}>
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      padding: '8px 16px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: '500',
                      textDecoration: 'none',
                      transition: 'all 0.3s',
                      backgroundColor: item.current ? '#dbeafe' : 'transparent',
                      color: item.current ? '#1d4ed8' : '#4b5563'
                    }}
                    onMouseEnter={(e) => {
                      if (!item.current) {
                        e.target.style.color = '#1d4ed8';
                        e.target.style.backgroundColor = '#eff6ff';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!item.current) {
                        e.target.style.color = '#4b5563';
                        e.target.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    {item.name}
                  </Link>
                ))}
              </div>
            </div>
            <div className="flex items-center">
              <div style={{ fontSize: '14px', color: '#6b7280' }}>
                Powered by AWS Services
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main style={{ paddingTop: '48px', paddingBottom: '48px' }}>
        <div className="animate-fade-in-up">
          {children}
        </div>
      </main>
    </div>
  );
};
