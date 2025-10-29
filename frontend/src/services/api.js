import axios from 'axios';

const api = axios.create({
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Get all categories
  async getCategories() {
    const response = await api.get('/api/categories');
    return response.data;
  },

  // Get all products
  async getProducts(params = {}) {
    const response = await api.get('/api/products', { params });
    return response.data;
  },

  // Get products by category
  async getProductsByCategory(category, params = {}) {
    const response = await api.get(`/api/products/category/${encodeURIComponent(category)}`, { params });
    return response.data;
  },

  // Get featured products for homepage
  async getFeaturedProducts(limit = 8) {
    const response = await api.get('/api/products/featured', { params: { limit } });
    return response.data;
  },

  // Get product details
  async getProductById(productId) {
    const response = await api.get(`/api/products/${productId}`);
    return response.data;
  }
};

export default api;
