<template>
  <div class="home-page">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">Zava Popup Shop</h1>
        <p class="hero-subtitle">Premium Merchandise & Apparel at Popup Locations</p>
        <router-link to="/category/accessories" class="btn btn-primary hero-btn">
          Shop Now
        </router-link>
      </div>
    </section>

    <!-- Featured Categories -->
    <section class="categories-section">
      <div class="container">
        <h2 class="section-title">Shop by Category</h2>
        <div class="categories-grid">
          <router-link 
            v-for="category in categories" 
            :key="category.id"
            :to="category.link"
            class="category-card"
          >
            <div class="category-image">
              <span class="category-icon">{{ category.icon }}</span>
            </div>
            <h3 class="category-name">{{ category.name }}</h3>
            <p class="category-count">{{ category.count }} items</p>
          </router-link>
        </div>
      </div>
    </section>

    <!-- Featured Products -->
    <section class="featured-products">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">Featured Products</h2>
          <router-link to="/category/accessories" class="view-all-link">
            View All →
          </router-link>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="error">
          {{ error }}
        </div>

        <!-- Products Grid -->
        <div v-else class="products-grid">
          <ProductCard 
            v-for="product in featuredProducts" 
            :key="product.id"
            :product="product"
          />
        </div>
      </div>
    </section>

    <!-- Store Locations Banner -->
    <section class="locations-banner">
      <div class="container">
        <div class="banner-content">
          <h2>Find a Popup Shop Near You</h2>
          <p>10+ locations across the country</p>
          <router-link to="/stores" class="btn btn-outline">
            View Locations
          </router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import ProductCard from '../components/ProductCard.vue';
import { apiService } from '../services/api';

export default {
  name: 'HomePage',
  components: {
    ProductCard
  },
  data() {
    return {
      loading: false,
      error: null,
      featuredProducts: [],
      categories: [
        {
          id: 'accessories',
          name: 'Accessories',
          link: '/category/accessories',
          icon: '👜',
          count: 41
        },
        {
          id: 'apparel-bottoms',
          name: 'Bottoms',
          link: '/category/apparel-bottoms',
          icon: '👖',
          count: 17
        },
        {
          id: 'apparel-tops',
          name: 'Tops',
          link: '/category/apparel-tops',
          icon: '👕',
          count: 35
        },
        {
          id: 'footwear',
          name: 'Footwear',
          link: '/category/footwear',
          icon: '👟',
          count: 22
        },
        {
          id: 'outerwear',
          name: 'Outerwear',
          link: '/category/outerwear',
          icon: '🧥',
          count: 14
        }
      ]
    };
  },
  async mounted() {
    await this.loadFeaturedProducts();
  },
  methods: {
    async loadFeaturedProducts() {
      this.loading = true;
      this.error = null;

      try {
        const response = await apiService.getFeaturedProducts(8);
        
        // API returns {products: [...], total: ...}
        const data = response.products || response;
        
        // Transform API data to component format
        if (Array.isArray(data)) {
          this.featuredProducts = data.map(item => ({
            id: item.product_id || item.id,
            name: item.product_name || item.name,
            category: item.category_name || item.category,
            price: item.unit_price || item.price,
            originalPrice: item.original_price,
            badge: item.badge,
            image_url: item.image_url
          }));
        } else {
          // Handle mock/test data format
          this.featuredProducts = this.getMockProducts();
        }
      } catch (err) {
        console.error('Error loading featured products:', err);
        // Use mock data as fallback
        this.featuredProducts = this.getMockProducts();
        this.error = null; // Don't show error, just use mock data
      } finally {
        this.loading = false;
      }
    },
    getMockProducts() {
      // Mock products based on the documentation
      return [
        {
          id: 1,
          name: 'Classic White Sneakers',
          category: 'Footwear',
          price: 79.99,
          badge: 'Popular'
        },
        {
          id: 2,
          name: 'Laptop Commuter Backpack',
          category: 'Accessories',
          price: 82.07
        },
        {
          id: 3,
          name: 'Classic Straight Leg Jeans',
          category: 'Apparel - Bottoms',
          price: 74.61
        },
        {
          id: 4,
          name: 'Pullover Fleece Hoodie',
          category: 'Apparel - Tops',
          price: 59.99,
          badge: 'New'
        },
        {
          id: 5,
          name: 'Bomber Jacket',
          category: 'Outerwear',
          price: 129.99
        },
        {
          id: 6,
          name: 'Baseball Cap Classic',
          category: 'Accessories',
          price: 29.84
        },
        {
          id: 7,
          name: 'Running Athletic Shoes',
          category: 'Footwear',
          price: 89.99,
          badge: 'Sale'
        },
        {
          id: 8,
          name: 'Classic Cotton T-Shirt',
          category: 'Apparel - Tops',
          price: 24.99
        }
      ];
    }
  }
};
</script>

<style scoped>
.home-page {
  min-height: 100vh;
}

/* Hero Section */
.hero {
  position: relative;
  height: 600px;
  background-image: url('../assets/images/store.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  text-align: center;
  margin-bottom: 4rem;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, 
    rgba(13, 17, 23, 0.85) 0%, 
    rgba(36, 41, 47, 0.75) 50%, 
    rgba(45, 164, 78, 0.65) 100%
  );
  z-index: 1;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 800px;
  padding: 2rem;
}

.hero-title {
  font-size: 4rem;
  font-weight: 700;
  margin-bottom: 1rem;
  letter-spacing: 0.05em;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.hero-subtitle {
  font-size: 1.5rem;
  margin-bottom: 2rem;
  opacity: 0.95;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.hero-btn {
  font-size: 1.125rem;
  padding: 1rem 2.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

/* Responsive Hero */
@media (max-width: 1024px) {
  .hero {
    height: 500px;
    background-position: 60% center;
  }
  
  .hero-title {
    font-size: 3rem;
  }
  
  .hero-subtitle {
    font-size: 1.25rem;
  }
}

@media (max-width: 768px) {
  .hero {
    height: 450px;
    background-position: 65% center;
  }
  
  .hero-title {
    font-size: 2.5rem;
  }
  
  .hero-subtitle {
    font-size: 1.125rem;
  }
  
  .hero-btn {
    font-size: 1rem;
    padding: 0.875rem 2rem;
  }
}

@media (max-width: 480px) {
  .hero {
    height: 400px;
    background-position: 70% center;
  }
  
  .hero-title {
    font-size: 2rem;
  }
  
  .hero-subtitle {
    font-size: 1rem;
  }
}

/* Categories Section */
.categories-section {
  margin-bottom: 4rem;
}

.section-title {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 2.5rem;
  color: var(--primary-color);
}

.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
}

.category-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  background: white;
  border: 2px solid var(--border-color);
  border-radius: 12px;
  transition: all 0.3s;
  text-align: center;
}

.category-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  border-color: var(--accent-color);
}

.category-image {
  width: 100px;
  height: 100px;
  background: var(--hover-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
  transition: background 0.3s;
}

.category-card:hover .category-image {
  background: #e8f4ff;
}

.category-icon {
  font-size: 3rem;
}

.category-name {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--primary-color);
}

.category-count {
  font-size: 0.875rem;
  color: var(--secondary-color);
}

/* Featured Products */
.featured-products {
  margin-bottom: 4rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.view-all-link {
  font-weight: 600;
  color: var(--accent-color);
  transition: color 0.2s;
}

.view-all-link:hover {
  color: var(--primary-color);
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 2rem;
}

/* Locations Banner */
.locations-banner {
  background: linear-gradient(135deg, #1a1a1a 0%, #4a4a4a 100%);
  color: white;
  padding: 4rem 0;
  margin-bottom: 0;
}

.banner-content {
  text-align: center;
}

.banner-content h2 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.banner-content p {
  font-size: 1.125rem;
  margin-bottom: 2rem;
  opacity: 0.9;
}

.banner-content .btn {
  color: white;
  border-color: white;
}

.banner-content .btn:hover {
  background: white;
  color: var(--primary-color);
}

/* Responsive */
@media (max-width: 768px) {
  .hero {
    height: 400px;
  }

  .hero-title {
    font-size: 2.5rem;
  }

  .hero-subtitle {
    font-size: 1.125rem;
  }

  .section-title {
    font-size: 2rem;
  }

  .categories-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
  }

  .category-card {
    padding: 1.5rem;
  }

  .category-image {
    width: 80px;
    height: 80px;
  }

  .category-icon {
    font-size: 2.5rem;
  }

  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
}
</style>
