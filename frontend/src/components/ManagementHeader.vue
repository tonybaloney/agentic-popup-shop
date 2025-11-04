<template>
  <header class="management-header">
    <div class="container">
      <div class="header-content">
        <div class="logo-section">
          <router-link to="/management" class="logo">
            <span class="logo-subtitle">Shop Management</span>
          </router-link>
        </div>

        <nav class="main-nav" :class="{ 'mobile-open': mobileMenuOpen }">
          <button class="mobile-close" @click="closeMobileMenu">×</button>
          
          <div class="nav-links">
            <router-link to="/management" class="nav-link" exact-active-class="active" @click="closeMobileMenu">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
              Dashboard
            </router-link>
            
            <router-link to="/management/suppliers" class="nav-link" @click="closeMobileMenu">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="8.5" cy="7" r="4"/>
                <polyline points="17 11 19 13 23 9"/>
              </svg>
              Suppliers
            </router-link>
            
            <router-link to="/management/inventory" class="nav-link" @click="closeMobileMenu">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
              Inventory
            </router-link>
            
            <router-link to="/management/products" class="nav-link" @click="closeMobileMenu">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
                <line x1="3" y1="6" x2="21" y2="6"/>
                <path d="M16 10a4 4 0 0 1-8 0"/>
              </svg>
              Products
            </router-link>
            
            <router-link to="/management/policies" class="nav-link" @click="closeMobileMenu">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
              Policies
            </router-link>
          </div>
        </nav>

        <div class="header-actions">
          <div class="user-info">
            <span class="user-name">{{ userName }}</span>
            <span class="user-role">{{ userRole }}</span>
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
  name: 'ManagementHeader',
  data() {
    return {
      mobileMenuOpen: false
    };
  },
  computed: {
    userName() {
      return authStore.user?.username || authStore.user?.store_name || 'User';
    },
    userRole() {
      return authStore.user?.role || 'Manager';
    }
  },
  methods: {
    toggleMobileMenu() {
      this.mobileMenuOpen = !this.mobileMenuOpen;
    },
    closeMobileMenu() {
      this.mobileMenuOpen = false;
    },
    async handleLogout() {
      await authStore.logout();
      this.$router.push('/');
    }
  }
};
</script>

<style scoped>
.management-header {
  background: var(--primary-color);
  color: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
  padding: 1rem 0;
}

.logo-section .logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: white;
}

.logo-subtitle {
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  opacity: 0.95;
}

.main-nav {
  flex: 1;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  color: rgba(255, 255, 255, 0.85);
  font-weight: 500;
  border-radius: 6px;
  transition: all 0.2s;
  font-size: 0.9rem;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-link.active {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.nav-link svg {
  flex-shrink: 0;
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
}

.user-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.user-role {
  font-size: 0.75rem;
  opacity: 0.8;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.mobile-menu-btn {
  display: none;
  padding: 0.5rem;
  color: white;
}

.mobile-close {
  display: none;
}

/* Mobile Responsive */
@media (max-width: 968px) {
  .user-info {
    display: none;
  }

  .logout-btn {
    padding: 0.5rem;
  }

  .logout-btn span {
    display: none;
  }

  .mobile-menu-btn {
    display: block;
  }

  .main-nav {
    position: fixed;
    top: 0;
    right: -100%;
    height: 100vh;
    width: 80%;
    max-width: 300px;
    background: var(--primary-color);
    box-shadow: -2px 0 10px rgba(0, 0, 0, 0.3);
    transition: right 0.3s ease;
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
    font-size: 2rem;
    color: white;
    background: none;
    border: none;
    cursor: pointer;
  }

  .nav-links {
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    padding-top: 4rem;
  }

  .nav-link {
    padding: 1rem 1.5rem;
    border-radius: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
}
</style>
