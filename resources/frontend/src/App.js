import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout.js';
import { Home } from './pages/Home.js';
import { LexPage } from './pages/LexPage.js';
import { PollyPage } from './pages/PollyPage.js';
import { ComprehendPage } from './pages/ComprehendPage.js';
import { RekognitionPage } from './pages/RekognitionPage.js';
import './index.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/lex" element={<LexPage />} />
          <Route path="/polly" element={<PollyPage />} />
          <Route path="/comprehend" element={<ComprehendPage />} />
          <Route path="/rekognition" element={<RekognitionPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
