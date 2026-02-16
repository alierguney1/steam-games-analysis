/**
 * API Client
 * Axios wrapper for backend API communication
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('token');
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const api = {
  // Health check
  health: () => apiClient.get('/health'),
  
  // Games endpoints
  games: {
    list: (params?: any) => apiClient.get('/api/games', { params }),
    get: (id: number) => apiClient.get(`/api/games/${id}`),
    search: (query: string) => apiClient.get('/api/games/search', { params: { q: query } }),
  },
  
  // Analytics endpoints
  analytics: {
    did: (params?: any) => apiClient.get('/api/analytics/did', { params }),
    survival: (params?: any) => apiClient.get('/api/analytics/survival', { params }),
    elasticity: (params?: any) => apiClient.get('/api/analytics/elasticity', { params }),
  },
  
  // Ingestion endpoints
  ingestion: {
    trigger: (type: string) => apiClient.post('/api/ingestion/trigger', { type }),
    status: () => apiClient.get('/api/ingestion/status'),
  },
  
  // Dashboard endpoints
  dashboard: {
    summary: () => apiClient.get('/api/dashboard/summary'),
    metrics: (params?: any) => apiClient.get('/api/dashboard/metrics', { params }),
  },
};
