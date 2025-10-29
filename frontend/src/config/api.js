import axios from 'axios';


export const config = {
  // wsBaseUrl: API_BASE_URL.replace(/^http[s]/, 'ws'),
  
  // Timeout for all API requests (in milliseconds)
  timeout: 3000, // 3 seconds
  
  endpoints: {
    categories: `/api/categories`,
    products: `/api/products`,
    productsByCategory: (category) => `/api/products/category/${encodeURIComponent(category)}`,
    featuredProducts: `/api/products/featured`,
    stores: `/api/stores`,
  },
  // Placeholder for product images - you'll add these later
  getProductImageUrl: (productId) => `/images/products/${productId}.jpg`,
  placeholderImage: '/images/placeholder.png'
};

// Create a pre-configured axios instance
export const apiClient = axios.create({
  timeout: config.timeout,
  headers: {
    'Content-Type': 'application/json'
  }
});
