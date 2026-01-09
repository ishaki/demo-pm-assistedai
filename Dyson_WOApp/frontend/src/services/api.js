import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed in the future
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.config.url} - ${response.status}`);
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);

    // Handle specific error cases
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;

      switch (status) {
        case 404:
          console.error('Resource not found');
          break;
        case 500:
          console.error('Server error occurred');
          break;
        default:
          console.error(`Error ${status}: ${data.detail || 'Unknown error'}`);
      }
    } else if (error.request) {
      // Request made but no response received
      console.error('No response from server. Please check your connection.');
    } else {
      // Error in request configuration
      console.error('Error:', error.message);
    }

    return Promise.reject(error);
  }
);

export default api;
