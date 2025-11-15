<template>
  <header class="app-header">
    <div class="header-branding">
      <router-link to="/" class="branding-link">
        <div class="branding-top">
          <img src="/zava-full-logo.png" alt="Zava Logo" class="header-logo" />
          <h1 class="header-title">Live Popup Shop</h1>
        </div>
      </router-link>
    </div>

    <nav class="main-nav">
      <router-link to="/" class="nav-link">Home</router-link>
      <router-link to="/category/footwear" class="nav-link">Footwear</router-link>
      <router-link to="/category/apparel-tops" class="nav-link">Tops</router-link>
      <router-link to="/category/apparel-bottoms" class="nav-link">Bottoms</router-link>
      <router-link to="/stores" class="nav-link">Stores</router-link>
    </nav>

    <div class="header-user">
      <template v-if="isAuthenticated">
        <div class="user-info">
          <span class="user-name">{{ username }}</span>
          <span class="user-role">{{ userRole === 'customer' ? 'Customer' : userRole === 'admin' ? 'Administrator' : 'Store Manager' }}</span>
        </div>
        <div class="user-avatar" @click="navigateToDashboard">
          <vibe-icon name="person"></vibe-icon>
        </div>
        <button class="logout-btn" @click="handleLogout" title="Logout">
          Logout
        </button>
      </template>
      <template v-else>
        <router-link to="/login" class="login-btn">Login</router-link>
      </template>
    </div>
  </header>
</template>

<script>
import { authStore } from '../stores/auth';

export default {
  name: 'AppHeader',
  computed: {
    isAuthenticated() {
      return authStore.isAuthenticated;
    },
    username() {
      return authStore.user?.username || authStore.user?.name || 'Guest';
    },
    userRole() {
      return authStore.user?.role || 'customer';
    }
  },
  methods: {
    navigateToDashboard() {
      if (this.userRole === 'customer') {
        this.$router.push('/customer/dashboard');
      } else if (this.userRole === 'admin' || this.userRole === 'store_manager') {
        this.$router.push('/management');
      }
    },
    async handleLogout() {
      await authStore.logout();
      this.$router.push('/');
    }
  }
};
</script>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #1e4a5c 0%, var(--primary-color) 100%);
  color: #f0f6fc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  font-family: "Mona Sans", -apple-system, BlinkMacSystemFont, "Segoe UI",
    "Noto Sans", Helvetica, Arial, sans-serif;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 1000;
}

.header-branding {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.branding-link {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  text-decoration: none;
  color: inherit;
}

.branding-top {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-logo {
  height: 40px;
  width: auto;
}

.header-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: #f0f6fc;
}

.main-nav {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  justify-content: center;
}

.nav-link {
  color: #f0f6fc;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: all 0.3s ease;
  font-size: 0.875rem;
  position: relative;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%) scaleX(0);
  width: 80%;
  height: 2px;
  background-color: #9EC9D9;
  transition: transform 0.3s ease, opacity 0.3s ease;
  opacity: 0;
}

.nav-link:hover {
  color: #9EC9D9;
  transform: translateY(-1px);
}

.nav-link.router-link-active {
  color: #f0f6fc;
}

.nav-link.router-link-active::after {
  transform: translateX(-50%) scaleX(1);
  opacity: 1;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.125rem;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: #f0f6fc;
}

.user-role {
  font-size: 0.75rem;
  color: #7d8590;
  font-weight: 400;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--border-color);
  font-size: 1.25rem;
  transition: all 0.2s ease;
  cursor: pointer;
}

.user-avatar:hover {
  background: var(--secondary-color);
  border-color: var(--accent-color);
  transform: scale(1.05);
}

.user-avatar i {
  color: white;
}

.login-btn {
  background: var(--primary-color);
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 2px solid var(--border-color);
  transition: all 0.2s ease;
  font-weight: 500;
}

.login-btn:hover {
  background: var(--secondary-color);
  border-color: var(--accent-color);
  transform: scale(1.05);
  text-decoration: none;
  color: white;
}

.logout-btn {
  background: transparent;
  border: 2px solid var(--border-color);
  color: #f0f6fc;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.logout-btn:hover {
  background: var(--secondary-color);
  border-color: var(--accent-color);
  transform: scale(1.05);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .app-header {
    padding: 0.75rem 1rem;
    flex-wrap: wrap;
  }

  .header-branding {
    order: 1;
    flex: 1;
  }

  .header-logo {
    height: 30px;
  }

  .header-title {
    font-size: 1.1rem;
  }

  .header-subtitle {
    font-size: 0.65rem;
  }

  .main-nav {
    order: 3;
    flex-basis: 100%;
    justify-content: flex-start;
    gap: 1rem;
    margin-top: 0.75rem;
    overflow-x: auto;
    padding-bottom: 0.5rem;
  }

  .nav-link {
    font-size: 0.8rem;
    padding: 0.4rem 0.8rem;
    white-space: nowrap;
  }

  .header-user {
    order: 2;
    gap: 0.75rem;
  }

  .user-info {
    display: none;
  }

  .user-avatar {
    width: 35px;
    height: 35px;
    font-size: 1.1rem;
  }

  .logout-btn {
    font-size: 0.8rem;
    padding: 0.4rem 0.8rem;
  }
}
</style>
