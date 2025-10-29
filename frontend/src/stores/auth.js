// Store for authentication state
import { reactive } from 'vue';
import axios from 'axios';

export const authStore = reactive({
  isAuthenticated: false,
  user: null,
  token: null,
  
  async login(username, password) {
    try {
      // Call the real authentication API
      const response = await axios.post(`/api/login`, {
        username,
        password
      });
      
      const { access_token, user_role, store_id, store_name } = response.data;
      
      // Store authentication data
      this.isAuthenticated = true;
      this.token = access_token;
      this.user = {
        username,
        role: user_role,
        store_id,
        store_name
      };
      
      // Persist to sessionStorage
      sessionStorage.setItem('auth_token', access_token);
      sessionStorage.setItem('auth_user', JSON.stringify(this.user));
      
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      const errorMessage = error.response?.data?.detail || 'Invalid username or password';
      return { success: false, error: errorMessage };
    }
  },
  
  logout() {
    this.isAuthenticated = false;
    this.user = null;
    this.token = null;
    sessionStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_user');
  },
  
  checkAuth() {
    const token = sessionStorage.getItem('auth_token');
    const userStr = sessionStorage.getItem('auth_user');
    
    if (token && userStr) {
      this.token = token;
      this.user = JSON.parse(userStr);
      this.isAuthenticated = true;
      return true;
    }
    return false;
  },
  
  getToken() {
    return this.token || sessionStorage.getItem('auth_token');
  }
});
