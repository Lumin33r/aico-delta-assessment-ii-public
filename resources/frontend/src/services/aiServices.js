// Vite uses import.meta.env for environment variables
// Use VITE_API_URL or default to empty string (proxy will handle it)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const chatWithBot = async (message) => {
  // TODO: Implement Lex chat
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Chat error:', error);
    throw error;
  }
};

export const convertTextToSpeech = async (text) => {
  // TODO: Implement Polly TTS
  try {
    const response = await fetch(`${API_BASE_URL}/api/text-to-speech`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch (error) {
    console.error('Text-to-speech error:', error);
    throw error;
  }
};

export const analyzeSentiment = async (text) => {
  // TODO: Implement Comprehend sentiment analysis
  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze-sentiment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Sentiment analysis error:', error);
    throw error;
  }
};

export const analyzeImage = async (imageFile) => {
  // TODO: Implement Rekognition image analysis
  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    
    const response = await fetch(`${API_BASE_URL}/api/analyze-image`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Image analysis error:', error);
    throw error;
  }
};
