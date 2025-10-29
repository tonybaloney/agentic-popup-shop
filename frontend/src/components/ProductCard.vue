<template>
  <div class="product-card">
    <router-link :to="`/product/${product.id}`" class="product-link">
      <div class="product-image-container">
        <img 
          :src="productImageUrl" 
          :alt="product.name"
          class="product-image"
          @error="handleImageError"
        />
        <div v-if="product.badge" class="product-badge">{{ product.badge }}</div>
      </div>
      
      <div class="product-info">
        <div class="product-category">{{ product.category }}</div>
        <h3 class="product-name">{{ product.name }}</h3>
        <div class="product-price">
          <span class="current-price">${{ formatPrice(product.price) }}</span>
          <span v-if="product.originalPrice" class="original-price">
            ${{ formatPrice(product.originalPrice) }}
          </span>
        </div>
      </div>
    </router-link>
    
    <button class="add-to-cart-btn" @click="handleAddToCart">
      Add to Cart
    </button>
  </div>
</template>

<script>
import { config } from '../config/api';

export default {
  name: 'ProductCard',
  props: {
    product: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      imageError: false
    };
  },
  computed: {
    productImageUrl() {
      if (this.imageError) {
        console.log(this.product.image_url);
        return config.placeholderImage;
      }
      // Use image_url from API if available, otherwise fall back to default
      if (this.product.image_url) {
        // If the image_url doesn't start with /, prepend /images/
        return this.product.image_url.startsWith('/') 
          ? this.product.image_url 
          : `/images/${this.product.image_url}`;
      }
      this.imageError=true;
      return config.placeholderImage;
    }
  },
  methods: {
    formatPrice(price) {
      return Number(price).toFixed(2);
    },
    handleImageError() {
      this.imageError = true;
    },
    handleAddToCart() {
      // Mock add to cart functionality
      alert(`Added ${this.product.name} to cart!`);
    }
  }
};
</script>

<style scoped>
.product-card {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
  border: 1px solid var(--border-color);
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}

.product-link {
  display: block;
  text-decoration: none;
  color: inherit;
}

.product-image-container {
  position: relative;
  width: 100%;
  padding-bottom: 120%;
  background: var(--hover-color);
  overflow: hidden;
}

.product-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.product-card:hover .product-image {
  transform: scale(1.05);
}

.product-badge {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  background: var(--accent-color);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.product-info {
  padding: 1rem;
  flex: 1;
}

.product-category {
  font-size: 0.75rem;
  color: var(--secondary-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.product-name {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  line-height: 1.3;
  min-height: 2.6em;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-price {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.current-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--primary-color);
}

.original-price {
  font-size: 1rem;
  color: var(--secondary-color);
  text-decoration: line-through;
}

.add-to-cart-btn {
  width: 100%;
  padding: 0.875rem;
  background: var(--primary-color);
  color: white;
  font-weight: 600;
  border: none;
  transition: background 0.3s;
  cursor: pointer;
}

.add-to-cart-btn:hover {
  background: var(--secondary-color);
}
</style>
