<template>
  <div class="product-page">
    <div class="container">
      <!-- Loading State -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <!-- Product Content -->
      <div v-else class="product-content">
        <div class="product-gallery">
          <div class="main-image">
            <img 
              :src="productImageUrl" 
              :alt="product.name"
              @error="handleImageError"
            />
          </div>
        </div>

        <div class="product-info-section">
          <nav class="breadcrumb">
            <router-link to="/">Home</router-link>
            <span class="separator">/</span>
            <router-link :to="`/category/${categorySlug}`">{{ product.category }}</router-link>
            <span class="separator">/</span>
            <span class="current">{{ product.name }}</span>
          </nav>

          <h1 class="product-title">{{ product.name }}</h1>
          
          <div class="product-price-section">
            <span class="product-price">${{ formatPrice(product.price) }}</span>
            <span v-if="product.originalPrice" class="original-price">
              ${{ formatPrice(product.originalPrice) }}
            </span>
          </div>

          <div class="product-description">
            <p>{{ product.description }}</p>
          </div>

          <!-- Size Selector (Mock) -->
          <div class="size-selector">
            <label class="selector-label">Size:</label>
            <div class="size-options">
              <button 
                v-for="size in sizes" 
                :key="size"
                class="size-btn"
                :class="{ active: selectedSize === size }"
                @click="selectedSize = size"
              >
                {{ size }}
              </button>
            </div>
          </div>

          <!-- Color Selector (Mock) -->
          <div class="color-selector">
            <label class="selector-label">Color:</label>
            <div class="color-options">
              <button 
                v-for="color in colors" 
                :key="color.name"
                class="color-btn"
                :class="{ active: selectedColor === color.name }"
                :style="{ backgroundColor: color.hex }"
                @click="selectedColor = color.name"
                :title="color.name"
              ></button>
            </div>
          </div>

          <!-- Quantity Selector -->
          <div class="quantity-selector">
            <label class="selector-label">Quantity:</label>
            <div class="quantity-controls">
              <button class="qty-btn" @click="decreaseQty">-</button>
              <input type="number" v-model.number="quantity" min="1" class="qty-input" />
              <button class="qty-btn" @click="increaseQty">+</button>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="action-buttons">
            <button class="btn btn-primary add-cart-btn" @click="handleAddToCart">
              Add to Cart
            </button>
            <button class="btn btn-outline wishlist-btn" @click="handleAddToWishlist">
              ♡ Add to Wishlist
            </button>
          </div>

          <!-- Product Details -->
          <div class="product-details">
            <div class="detail-section">
              <h3>Product Details</h3>
              <ul>
                <li><strong>Category:</strong> {{ product.category }}</li>
                <li><strong>Type:</strong> {{ product.type }}</li>
                <li><strong>Material:</strong> Premium quality fabric</li>
                <li><strong>Care:</strong> Machine washable</li>
              </ul>
            </div>

            <div class="detail-section">
              <h3>Availability</h3>
              <p class="stock-status in-stock">✓ In Stock at multiple locations</p>
              <router-link to="/stores" class="check-stores-link">
                Check store availability →
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { config } from '../config/api';
import { apiService } from '../services/api';

export default {
  name: 'ProductPage',
  data() {
    return {
      loading: false,
      imageError: false,
      product: {
        id: null,
        name: '',
        category: '',
        type: '',
        price: 0,
        originalPrice: null,
        description: 'High-quality product crafted with attention to detail. Perfect for everyday wear and special occasions.',
        imageUrl: 'placeholder.png'
      },
      selectedSize: 'M',
      sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
      selectedColor: 'Black',
      colors: [
        { name: 'Black', hex: '#000000' },
        { name: 'White', hex: '#FFFFFF' },
        { name: 'Gray', hex: '#808080' },
        { name: 'Navy', hex: '#001f3f' },
        { name: 'Blue', hex: '#0074D9' }
      ],
      quantity: 1
    };
  },
  computed: {
    productId() {
      return this.$route.params.id;
    },
    categorySlug() {
      return this.product.category.toLowerCase().replace(/\s+/g, '-');
    },
    productImageUrl() {
      if (this.imageError) {
        return config.placeholderImage;
      }
      return `/images/${this.product.imageUrl}`;
    }
  },
  async mounted() {
    await this.loadProduct();
  },
  methods: {
    async loadProduct() {
      this.loading = true;

      try {
        const data = await apiService.getProductById(this.productId);
        
        this.product = {
          id: data.product_id || data.id,
          name: data.product_name || data.name,
          category: data.category_name || data.category || 'Apparel',
          type: data.product_type || data.type || 'General',
          price: data.unit_price || data.price || 49.99,
          originalPrice: data.original_price,
          description: data.description || this.product.description,
          imageUrl: data.image_url,
        };
      } catch (err) {
        console.error('Error loading product:', err);
        // Use mock data
        this.product = this.getMockProduct();
      } finally {
        this.loading = false;
      }
    },
    getMockProduct() {
      return {
        id: this.productId,
        name: 'Premium Product',
        category: 'Apparel',
        type: 'Clothing',
        price: 79.99,
        description: 'High-quality product crafted with attention to detail. Perfect for everyday wear and special occasions. Made with premium materials for lasting comfort and style.'
      };
    },
    formatPrice(price) {
      return Number(price).toFixed(2);
    },
    handleImageError() {
      this.imageError = true;
    },
    decreaseQty() {
      if (this.quantity > 1) {
        this.quantity--;
      }
    },
    increaseQty() {
      this.quantity++;
    },
    handleAddToCart() {
      alert(`Added ${this.quantity} x ${this.product.name} (${this.selectedSize}, ${this.selectedColor}) to cart!`);
    },
    handleAddToWishlist() {
      alert(`Added ${this.product.name} to wishlist!`);
    }
  }
};
</script>

<style scoped>
.product-page {
  min-height: 100vh;
  padding: 2rem 0;
}

.product-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  margin-top: 2rem;
}

.product-gallery {
  position: sticky;
  top: 100px;
  height: fit-content;
}

.main-image {
  width: 100%;
  aspect-ratio: 3/4;
  background: var(--hover-color);
  border-radius: 12px;
  overflow: hidden;
}

.main-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-info-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--secondary-color);
}

.breadcrumb a {
  color: var(--accent-color);
}

.separator {
  color: var(--border-color);
}

.current {
  color: var(--text-color);
}

.product-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--primary-color);
  margin: 0;
}

.product-price-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.product-price {
  font-size: 2rem;
  font-weight: 700;
  color: var(--primary-color);
}

.original-price {
  font-size: 1.5rem;
  color: var(--secondary-color);
  text-decoration: line-through;
}

.product-description {
  color: var(--text-color);
  line-height: 1.6;
}

.selector-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--text-color);
}

.size-options {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.size-btn {
  padding: 0.75rem 1.25rem;
  border: 2px solid var(--border-color);
  border-radius: 4px;
  background: white;
  font-weight: 600;
  transition: all 0.2s;
}

.size-btn:hover,
.size-btn.active {
  border-color: var(--primary-color);
  background: var(--primary-color);
  color: white;
}

.color-options {
  display: flex;
  gap: 0.75rem;
}

.color-btn {
  width: 40px;
  height: 40px;
  border: 3px solid transparent;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
}

.color-btn:hover,
.color-btn.active {
  border-color: var(--primary-color);
  transform: scale(1.1);
}

.quantity-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.qty-btn {
  width: 40px;
  height: 40px;
  border: 2px solid var(--border-color);
  border-radius: 4px;
  background: white;
  font-size: 1.25rem;
  font-weight: 600;
  transition: all 0.2s;
}

.qty-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.qty-input {
  width: 80px;
  height: 40px;
  border: 2px solid var(--border-color);
  border-radius: 4px;
  text-align: center;
  font-size: 1rem;
  font-weight: 600;
}

.qty-input:focus {
  outline: none;
  border-color: var(--accent-color);
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.add-cart-btn,
.wishlist-btn {
  flex: 1;
  padding: 1rem 2rem;
  font-size: 1rem;
  font-weight: 600;
}

.product-details {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid var(--border-color);
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h3 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: var(--primary-color);
}

.detail-section ul {
  list-style: none;
}

.detail-section li {
  padding: 0.5rem 0;
  color: var(--text-color);
}

.stock-status {
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.stock-status.in-stock {
  color: #28a745;
}

.check-stores-link {
  color: var(--accent-color);
  font-weight: 600;
}

/* Responsive */
@media (max-width: 968px) {
  .product-content {
    grid-template-columns: 1fr;
    gap: 2rem;
  }

  .product-gallery {
    position: relative;
    top: 0;
  }

  .product-title {
    font-size: 1.5rem;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
