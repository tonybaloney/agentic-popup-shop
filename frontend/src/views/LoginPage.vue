<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <p class="login-subtitle">Shop Management</p>
        </div>

        <form @submit.prevent="handleLogin" class="login-form">
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <div class="form-group">
            <label for="username">Username</label>
            <input
              id="username"
              v-model="username"
              type="text"
              placeholder="Enter username"
              required
              autofocus
            />
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <input
              id="password"
              v-model="password"
              type="password"
              placeholder="Enter password"
              required
            />
          </div>

          <button type="submit" class="btn btn-primary login-btn" :disabled="loading">
            {{ loading ? 'Logging in...' : 'Login' }}
          </button>
        </form>

        <div class="login-footer">
          <router-link to="/" class="back-link">← Back to Store</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { authStore } from '../stores/auth';

export default {
  name: 'LoginPage',
  data() {
    return {
      username: '',
      password: '',
      error: null,
      loading: false
    };
  },
  methods: {
    async handleLogin() {
      this.error = null;
      this.loading = true;

      try {
        const result = await authStore.login(this.username, this.password);
        
        if (result.success) {
          this.$router.push('/management');
        } else {
          this.error = result.error || 'Invalid username or password';
        }
      } catch (error) {
        this.error = 'An error occurred during login. Please try again.';
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.login-container {
  width: 100%;
  max-width: 450px;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 3rem;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.login-subtitle {
  font-size: 1.125rem;
  color: var(--secondary-color);
  letter-spacing: -0.01em;
  font-weight: 600;
}

.login-form {
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--text-color);
}

.form-group input {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent-color);
}

.error-message {
  padding: 1rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c00;
  margin-bottom: 1.5rem;
  text-align: center;
  font-weight: 500;
}

.login-btn {
  width: 100%;
  padding: 1rem;
  font-size: 1.125rem;
  font-weight: 600;
  border-radius: 8px;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-footer {
  text-align: center;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
}

.demo-notice {
  font-size: 0.875rem;
  color: var(--secondary-color);
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: var(--hover-color);
  border-radius: 6px;
}

.back-link {
  color: var(--accent-color);
  font-weight: 600;
  font-size: 0.9rem;
  transition: color 0.2s;
}

.back-link:hover {
  color: var(--primary-color);
}

@media (max-width: 768px) {
  .login-card {
    padding: 2rem;
  }

  .login-logo {
    font-size: 2.5rem;
  }
}
</style>
