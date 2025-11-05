<template>
  <header class="marketing-header">
    <div class="container">
      <div class="header-content">
        <div class="logo-section">
          <router-link to="/marketing" class="logo">
            <span class="logo-text">GitHub Popup Store</span>
            <span class="logo-subtitle">Marketing Dashboard</span>
          </router-link>
        </div>

        <nav class="main-nav" :class="{ 'mobile-open': mobileMenuOpen }">
          <button class="mobile-close" @click="closeMobileMenu">×</button>
          
          <div class="nav-links">
            <router-link to="/marketing" class="nav-link" exact-active-class="active" @click="closeMobileMenu">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
              Campaign Planner
            </router-link>
          </div>
        </nav>

        <div class="header-actions">
          <div class="user-info">
            <span class="user-name">{{ userName }}</span>
            <span class="user-role">Marketing Manager</span>
          </div>
          <button class="logout-btn" @click="handleLogout">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Logout
          </button>
          <button class="mobile-menu-btn" @click="toggleMobileMenu">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M3 12H21M3 6H21M3 18H21" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
import { authStore } from '../stores/auth';

export default {
  name: 'MarketingHeader',
  data() {
    return {
      mobileMenuOpen: false
    };
  },
  computed: {
    userName() {
      return authStore.user?.name || authStore.user?.username || 'Marketing User';
    }
  },
  methods: {
    handleLogout() {
      authStore.logout();
      this.$router.push('/login');
    },
    toggleMobileMenu() {
      this.mobileMenuOpen = !this.mobileMenuOpen;
    },
    closeMobileMenu() {
      this.mobileMenuOpen = false;
    }
  }
};
</script>

<style scoped>
.marketing-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 70px;
}

.logo-section {
  flex-shrink: 0;
}

.logo {
  display: flex;
  flex-direction: column;
  text-decoration: none;
  color: white;
  gap: 0.25rem;
}

.logo-text {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.logo-subtitle {
  font-size: 0.85rem;
  opacity: 0.9;
  font-weight: 400;
}

.main-nav {
  flex: 1;
  display: flex;
  justify-content: center;
}

.mobile-close {
  display: none;
}

.nav-links {
  display: flex;
  gap: 0.5rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s;
  white-space: nowrap;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.nav-link.active {
  background: rgba(255, 255, 255, 0.25);
  color: white;
  font-weight: 600;
}

.nav-link svg {
  stroke-width: 2;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.125rem;
}

.user-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.user-role {
  font-size: 0.8rem;
  opacity: 0.85;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-1px);
}

.logout-btn svg {
  stroke-width: 2;
}

.mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 0.5rem;
}

@media (max-width: 768px) {
  .header-content {
    min-height: 60px;
  }

  .logo-text {
    font-size: 1.1rem;
  }

  .logo-subtitle {
    font-size: 0.75rem;
  }

  .main-nav {
    position: fixed;
    top: 0;
    right: -100%;
    width: 80%;
    max-width: 300px;
    height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    flex-direction: column;
    justify-content: flex-start;
    padding: 2rem 1rem;
    transition: right 0.3s ease;
    box-shadow: -4px 0 12px rgba(0, 0, 0, 0.2);
    z-index: 1001;
  }

  .main-nav.mobile-open {
    right: 0;
  }

  .mobile-close {
    display: block;
    position: absolute;
    top: 1rem;
    right: 1rem;
    background: none;
    border: none;
    color: white;
    font-size: 2rem;
    cursor: pointer;
    line-height: 1;
    padding: 0.25rem;
  }

  .nav-links {
    flex-direction: column;
    width: 100%;
    gap: 0.5rem;
  }

  .nav-link {
    width: 100%;
    justify-content: flex-start;
  }

  .user-info {
    display: none;
  }

  .logout-btn {
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
  }

  .mobile-menu-btn {
    display: block;
  }
}
</style>
