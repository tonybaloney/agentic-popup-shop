<template>
  <div class="category-page">
    <div class="container">
      <!-- Breadcrumb -->
      <nav class="breadcrumb">
        <router-link to="/">Home</router-link>
        <span class="separator">/</span>
        <span class="current">{{ categoryTitle }}</span>
      </nav>

      <!-- Category Header -->
      <div class="category-header">
        <h1 class="category-title">{{ categoryTitle }}</h1>
        <p class="category-description">{{ categoryDescription }}</p>
      </div>

      <!-- Filters and Sort (Placeholder) -->
      <div class="filters-bar">
        <div class="filter-group">
          <label>Sort by:</label>
          <select v-model="sortBy" class="filter-select">
            <option value="featured">Featured</option>
            <option value="price-low">Price: Low to High</option>
            <option value="price-high">Price: High to Low</option>
            <option value="name">Name: A-Z</option>
          </select>
        </div>
        <div class="results-count">
          {{ products.length }} products
        </div>
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
      <div v-else-if="products.length > 0" class="products-grid">
        <ProductCard 
          v-for="product in sortedProducts" 
          :key="product.id"
          :product="product"
        />
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <p>No products found in this category.</p>
        <router-link to="/" class="btn btn-primary">
          Back to Home
        </router-link>
      </div>
    </div>
  </div>
</template>

<script>
import ProductCard from '../components/ProductCard.vue';
import { apiService } from '../services/api';

export default {
  name: 'CategoryPage',
  components: {
    ProductCard
  },
  data() {
    return {
      loading: false,
      error: null,
      products: [],
      sortBy: 'featured'
    };
  },
  computed: {
    categorySlug() {
      return this.$route.params.category;
    },
    subcategorySlug() {
      return this.$route.params.subcategory;
    },
    categoryTitle() {
      return this.formatCategoryName(this.subcategorySlug || this.categorySlug);
    },
    categoryDescription() {
      const descriptions = {
        'accessories': 'Complete your look with our premium accessories collection',
        'apparel-bottoms': 'Comfortable and stylish bottoms for every occasion',
        'apparel-tops': 'Versatile tops to elevate your wardrobe',
        'footwear': 'Step out in style with our curated footwear collection',
        'outerwear': 'Stay warm and fashionable with quality outerwear',
        'backpacks-bags': 'Functional and stylish bags for everyday use',
        'jeans': 'Premium denim in various fits and washes',
        'sneakers': 'Comfort meets style in our sneaker collection'
      };
      return descriptions[this.subcategorySlug || this.categorySlug] || 
             'Discover our collection of quality products';
    },
    sortedProducts() {
      const sorted = [...this.products];
      
      switch (this.sortBy) {
        case 'price-low':
          return sorted.sort((a, b) => a.price - b.price);
        case 'price-high':
          return sorted.sort((a, b) => b.price - a.price);
        case 'name':
          return sorted.sort((a, b) => a.name.localeCompare(b.name));
        default:
          return sorted;
      }
    }
  },
  watch: {
    '$route.params': {
      handler() {
        this.loadProducts();
      },
      immediate: true
    }
  },
  methods: {
    formatCategoryName(slug) {
      if (!slug) return '';
      return slug
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    },
    async loadProducts() {
      this.loading = true;
      this.error = null;

      try {
        const category = this.subcategorySlug || this.categorySlug;
        const response = await apiService.getProductsByCategory(category);
        
        // API returns {products: [...], total: ...}
        const data = response.products || response;
        
        // Transform API data
        if (Array.isArray(data)) {
          this.products = data.map(item => ({
            id: item.product_id || item.id,
            name: item.product_name || item.name,
            category: item.category_name || item.category,
            price: item.unit_price || item.price,
            originalPrice: item.original_price,
            badge: item.badge,
            image_url: item.image_url
          }));
        } else {
          this.products = this.getMockProducts(category);
        }
      } catch (err) {
        console.error('Error loading products:', err);
        // Use mock data as fallback
        this.products = this.getMockProducts(this.subcategorySlug || this.categorySlug);
        this.error = null;
      } finally {
        this.loading = false;
      }
    },
    getMockProducts(category) {
      // Mock products based on category
      const mockData = {
        'accessories': [
          { id: 101, name: 'Canvas Tote Bag', category: 'Accessories', price: 34.99 },
          { id: 102, name: 'Laptop Commuter Backpack', category: 'Accessories', price: 82.07 },
          { id: 103, name: 'Baseball Cap Classic', category: 'Accessories', price: 29.84 },
          { id: 104, name: 'Leather Dress Belt', category: 'Accessories', price: 44.76 },
          { id: 105, name: 'Cashmere Blend Scarf', category: 'Accessories', price: 59.99 },
          { id: 106, name: 'Classic Aviator Sunglasses', category: 'Accessories', price: 79.99 }
        ],
        'apparel-bottoms': [
          { id: 201, name: 'Classic Straight Leg Jeans', category: 'Apparel - Bottoms', price: 74.61 },
          { id: 202, name: 'Skinny Fit Jeans', category: 'Apparel - Bottoms', price: 69.99 },
          { id: 203, name: 'Cargo Pants Utility', category: 'Apparel - Bottoms', price: 64.99 },
          { id: 204, name: 'Chino Pants', category: 'Apparel - Bottoms', price: 54.99 },
          { id: 205, name: 'Athletic Running Shorts', category: 'Apparel - Bottoms', price: 39.99 }
        ],
        'apparel-tops': [
          { id: 301, name: 'Classic Cotton T-Shirt', category: 'Apparel - Tops', price: 24.99 },
          { id: 302, name: 'Pullover Fleece Hoodie', category: 'Apparel - Tops', price: 59.99, badge: 'Popular' },
          { id: 303, name: 'Classic Plaid Flannel', category: 'Apparel - Tops', price: 49.99 },
          { id: 304, name: 'Oxford Button-Down Shirt', category: 'Apparel - Tops', price: 64.99 },
          { id: 305, name: 'Crewneck Sweatshirt', category: 'Apparel - Tops', price: 44.99 }
        ],
        'footwear': [
          { id: 401, name: 'Classic White Sneakers', category: 'Footwear', price: 79.99, badge: 'Popular' },
          { id: 402, name: 'Running Athletic Shoes', category: 'Footwear', price: 89.99 },
          { id: 403, name: 'Waterproof Hiking Boots', category: 'Footwear', price: 129.99 },
          { id: 404, name: 'Oxford Leather Shoes', category: 'Footwear', price: 119.99 },
          { id: 405, name: 'Sport Sandals', category: 'Footwear', price: 49.99 }
        ],
        'outerwear': [
          { id: 501, name: 'Bomber Jacket', category: 'Outerwear', price: 129.99 },
          { id: 502, name: 'Denim Jacket Classic', category: 'Outerwear', price: 89.99 },
          { id: 503, name: 'Puffer Jacket', category: 'Outerwear', price: 149.99, badge: 'New' },
          { id: 504, name: 'Rain Jacket Waterproof', category: 'Outerwear', price: 99.99 },
          { id: 505, name: 'Peacoat Wool Blend', category: 'Outerwear', price: 179.99 }
        ]
      };

      // Return products for the specific category or empty array
      return mockData[category] || [];
    }
  }
};
</script>

<style scoped>
.category-page {
  min-height: 100vh;
  padding: 2rem 0;
}

/* Breadcrumb */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--secondary-color);
  margin-bottom: 2rem;
}

.breadcrumb a {
  color: var(--accent-color);
  transition: color 0.2s;
}

.breadcrumb a:hover {
  color: var(--primary-color);
}

.separator {
  color: var(--border-color);
}

.current {
  color: var(--text-color);
  font-weight: 500;
}

/* Category Header */
.category-header {
  text-align: center;
  margin-bottom: 3rem;
}

.category-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: var(--primary-color);
}

.category-description {
  font-size: 1.125rem;
  color: var(--secondary-color);
}

/* Filters Bar */
.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 2rem;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.filter-group label {
  font-weight: 600;
  color: var(--text-color);
}

.filter-select {
  padding: 0.5rem 1rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 0.875rem;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.filter-select:focus {
  outline: none;
  border-color: var(--accent-color);
}

.results-count {
  font-size: 0.875rem;
  color: var(--secondary-color);
  font-weight: 500;
}

/* Products Grid */
.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-state p {
  font-size: 1.125rem;
  color: var(--secondary-color);
  margin-bottom: 2rem;
}

/* Responsive */
@media (max-width: 768px) {
  .category-title {
    font-size: 2rem;
  }

  .filters-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .filter-group {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-select {
    width: 100%;
  }

  .results-count {
    text-align: center;
  }

  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
  }
}
</style>
