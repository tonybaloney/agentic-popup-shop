import axios from 'axios';
import { authStore } from '../stores/auth';

const customerApi = axios.create({
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add request interceptor to include auth token
customerApi.interceptors.request.use(
  (config) => {
    const token = authStore.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log('Customer API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
customerApi.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('Customer API Error:', error.response?.status, error.message);
    if (error.response?.status === 401) {
      // Token expired or invalid
      authStore.logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const customerService = {
  // Get customer orders
  async getOrders() {
    const response = await customerApi.get('/api/users/orders');
    return response.data;
  }
};

export default customerApi;
