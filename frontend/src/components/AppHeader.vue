<template>
  <header class="header">
    <div class="header-top">
      <div class="container">
        <div class="header-top-content">
          <span class="header-message">Free shipping on orders over $50</span>
          <div class="header-actions">
            <router-link to="/login" class="header-link">Login</router-link>
            <span class="divider">|</span>
            <button class="header-link" @click="handleSignup">Sign Up</button>
          </div>
        </div>
      </div>
    </div>

    <div class="header-main">
      <div class="container">
        <div class="header-content">
          <router-link to="/" class="logo">
            <span class="logo-subtitle">Zava Shop</span>
          </router-link>

          <nav class="main-nav" :class="{ 'mobile-open': mobileMenuOpen }">
            <button class="mobile-close" @click="closeMobileMenu">×</button>
            
            <div class="nav-links">
              <router-link to="/" class="nav-link" @click="closeMobileMenu">Home</router-link>
              
              <div 
                class="nav-dropdown"
                @mouseenter="openDropdown('accessories')"
                @mouseleave="closeDropdown"
              >
                <router-link to="/category/accessories" class="nav-link">
                  Accessories
                  <span class="dropdown-arrow">▾</span>
                </router-link>
                <div v-if="activeDropdown === 'accessories'" class="dropdown-menu">
                  <router-link to="/category/accessories/backpacks-bags" class="dropdown-item" @click="closeMobileMenu">Backpacks & Bags</router-link>
                  <router-link to="/category/accessories/belts" class="dropdown-item" @click="closeMobileMenu">Belts</router-link>
                  <router-link to="/category/accessories/caps-hats" class="dropdown-item" @click="closeMobileMenu">Caps & Hats</router-link>
                  <router-link to="/category/accessories/gloves" class="dropdown-item" @click="closeMobileMenu">Gloves</router-link>
                  <router-link to="/category/accessories/scarves" class="dropdown-item" @click="closeMobileMenu">Scarves</router-link>
                  <router-link to="/category/accessories/socks" class="dropdown-item" @click="closeMobileMenu">Socks</router-link>
                  <router-link to="/category/accessories/sunglasses" class="dropdown-item" @click="closeMobileMenu">Sunglasses</router-link>
                </div>
              </div>

              <div 
                class="nav-dropdown"
                @mouseenter="openDropdown('bottoms')"
                @mouseleave="closeDropdown"
              >
                <router-link to="/category/apparel-bottoms" class="nav-link">
                  Bottoms
                  <span class="dropdown-arrow">▾</span>
                </router-link>
                <div v-if="activeDropdown === 'bottoms'" class="dropdown-menu">
                  <router-link to="/category/apparel-bottoms/jeans" class="dropdown-item" @click="closeMobileMenu">Jeans</router-link>
                  <router-link to="/category/apparel-bottoms/pants" class="dropdown-item" @click="closeMobileMenu">Pants</router-link>
                  <router-link to="/category/apparel-bottoms/shorts" class="dropdown-item" @click="closeMobileMenu">Shorts</router-link>
                </div>
              </div>

              <div 
                class="nav-dropdown"
                @mouseenter="openDropdown('tops')"
                @mouseleave="closeDropdown"
              >
                <router-link to="/category/apparel-tops" class="nav-link">
                  Tops
                  <span class="dropdown-arrow">▾</span>
                </router-link>
                <div v-if="activeDropdown === 'tops'" class="dropdown-menu">
                  <router-link to="/category/apparel-tops/flannel-shirts" class="dropdown-item" @click="closeMobileMenu">Flannel Shirts</router-link>
                  <router-link to="/category/apparel-tops/formal-shirts" class="dropdown-item" @click="closeMobileMenu">Formal Shirts</router-link>
                  <router-link to="/category/apparel-tops/hoodies" class="dropdown-item" @click="closeMobileMenu">Hoodies</router-link>
                  <router-link to="/category/apparel-tops/sweatshirts" class="dropdown-item" @click="closeMobileMenu">Sweatshirts</router-link>
                  <router-link to="/category/apparel-tops/t-shirts" class="dropdown-item" @click="closeMobileMenu">T-Shirts</router-link>
                </div>
              </div>

              <div 
                class="nav-dropdown"
                @mouseenter="openDropdown('footwear')"
                @mouseleave="closeDropdown"
              >
                <router-link to="/category/footwear" class="nav-link">
                  Footwear
                  <span class="dropdown-arrow">▾</span>
                </router-link>
                <div v-if="activeDropdown === 'footwear'" class="dropdown-menu">
                  <router-link to="/category/footwear/boots" class="dropdown-item" @click="closeMobileMenu">Boots</router-link>
                  <router-link to="/category/footwear/dress-shoes" class="dropdown-item" @click="closeMobileMenu">Dress Shoes</router-link>
                  <router-link to="/category/footwear/sandals" class="dropdown-item" @click="closeMobileMenu">Sandals</router-link>
                  <router-link to="/category/footwear/sneakers" class="dropdown-item" @click="closeMobileMenu">Sneakers</router-link>
                </div>
              </div>

              <div 
                class="nav-dropdown"
                @mouseenter="openDropdown('outerwear')"
                @mouseleave="closeDropdown"
              >
                <router-link to="/category/outerwear" class="nav-link">
                  Outerwear
                  <span class="dropdown-arrow">▾</span>
                </router-link>
                <div v-if="activeDropdown === 'outerwear'" class="dropdown-menu">
                  <router-link to="/category/outerwear/coats" class="dropdown-item" @click="closeMobileMenu">Coats</router-link>
                  <router-link to="/category/outerwear/jackets" class="dropdown-item" @click="closeMobileMenu">Jackets</router-link>
                </div>
              </div>

              <router-link to="/stores" class="nav-link" @click="closeMobileMenu">Stores</router-link>
            </div>
          </nav>

          <div class="header-icons">
            <button class="icon-btn" @click="handleSearch" aria-label="Search">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <circle cx="9" cy="9" r="7" stroke="currentColor" stroke-width="2"/>
                <path d="M14 14L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
            <button class="icon-btn" @click="handleCart" aria-label="Cart">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M1 1H3L3.4 3M5 11H15L19 3H3.4M5 11L3.4 3M5 11L3 15H17M7 18C7 18.5523 6.55228 19 6 19C5.44772 19 5 18.5523 5 18C5 17.4477 5.44772 17 6 17C6.55228 17 7 17.4477 7 18ZM17 18C17 18.5523 16.5523 19 16 19C15.4477 19 15 18.5523 15 18C15 17.4477 15.4477 17 16 17C16.5523 17 17 17.4477 17 18Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span v-if="cartCount > 0" class="cart-badge">{{ cartCount }}</span>
            </button>
            <button class="mobile-menu-btn" @click="toggleMobileMenu" aria-label="Menu">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M3 12H21M3 6H21M3 18H21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
export default {
  name: 'AppHeader',
  data() {
    return {
      activeDropdown: null,
      mobileMenuOpen: false,
      cartCount: 0 // Mock cart count
    };
  },
  methods: {
    openDropdown(menu) {
      this.activeDropdown = menu;
    },
    closeDropdown() {
      this.activeDropdown = null;
    },
    toggleMobileMenu() {
      this.mobileMenuOpen = !this.mobileMenuOpen;
    },
    closeMobileMenu() {
      this.mobileMenuOpen = false;
      this.activeDropdown = null;
    },
    handleSignup() {
      alert('Sign up feature - Coming soon!');
    },
    handleSearch() {
      alert('Search feature - Coming soon!');
    },
    handleCart() {
      alert('Cart feature - Coming soon!');
    }
  }
};
</script>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.header-top {
  background: var(--primary-color);
  color: white;
  padding: 0.5rem 0;
  font-size: 0.875rem;
}

.header-top-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-message {
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-link {
  color: white;
  font-size: 0.875rem;
  transition: opacity 0.2s;
}

.header-link:hover {
  opacity: 0.8;
}

.divider {
  color: rgba(255, 255, 255, 0.5);
}

.header-main {
  padding: 1rem 0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.logo-subtitle {
  font-size: 1rem;
  font-weight: 600;
  color: var(--primary-color);
  letter-spacing: -0.01em;
}

.main-nav {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 500;
  color: var(--text-color);
  padding: 0.5rem 0;
  transition: color 0.2s;
}

.nav-link:hover {
  color: var(--accent-color);
}

.nav-dropdown {
  position: relative;
}

.dropdown-arrow {
  font-size: 0.75rem;
  transition: transform 0.2s;
}

.nav-dropdown:hover .dropdown-arrow {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  min-width: 200px;
  padding: 0.5rem 0;
  margin-top: 0.5rem;
}

.dropdown-item {
  display: block;
  padding: 0.75rem 1.5rem;
  color: var(--text-color);
  transition: background-color 0.2s;
}

.dropdown-item:hover {
  background-color: var(--hover-color);
  color: var(--accent-color);
}

.header-icons {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.icon-btn {
  position: relative;
  padding: 0.5rem;
  color: var(--text-color);
  transition: color 0.2s;
}

.icon-btn:hover {
  color: var(--accent-color);
}

.cart-badge {
  position: absolute;
  top: 0;
  right: 0;
  background: var(--accent-color);
  color: white;
  font-size: 0.625rem;
  font-weight: 600;
  padding: 0.125rem 0.375rem;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.mobile-menu-btn {
  display: none;
  padding: 0.5rem;
  color: var(--text-color);
}

.mobile-close {
  display: none;
}

/* Mobile Responsive */
@media (max-width: 968px) {
  .header-top-content {
    font-size: 0.75rem;
  }

  .logo h1 {
    font-size: 1.5rem;
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
    background: white;
    box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
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
    color: var(--text-color);
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
    border-bottom: 1px solid var(--border-color);
  }

  .nav-dropdown .dropdown-menu {
    position: static;
    box-shadow: none;
    border: none;
    border-top: 1px solid var(--border-color);
    margin: 0;
    padding-left: 1rem;
    background: var(--hover-color);
  }

  .dropdown-item {
    padding: 0.5rem 1.5rem;
  }
}
</style>
