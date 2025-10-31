<template>
  <div class="customer-dashboard">
    <div class="container">
      <!-- Loading State -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <!-- Dashboard Content -->
      <div v-else>
        <!-- Welcome Banner -->
        <div class="welcome-banner">
          <div class="banner-content">
            <h1 class="welcome-title">Welcome back, {{ username }}! 👋</h1>
            <p class="welcome-subtitle">Here's a summary of your recent orders</p>
          </div>
        </div>

        <!-- Quick Stats -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon orders">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
                <line x1="3" y1="6" x2="21" y2="6"/>
              </svg>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ orderStats.totalOrders }}</div>
              <div class="stat-label">Total Orders</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon items">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="9" cy="21" r="1"/>
                <circle cx="20" cy="21" r="1"/>
                <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
              </svg>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ orderStats.totalItems }}</div>
              <div class="stat-label">Items Purchased</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon savings">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"/>
                <path d="M4 6v12c0 1.1.9 2 2 2h14v-4"/>
                <path d="M18 12a2 2 0 0 0-2 2c0 1.1.9 2 2 2h4v-4h-4z"/>
              </svg>
            </div>
            <div class="stat-content">
              <div class="stat-value">${{ formatCurrency(orderStats.totalSavings) }}</div>
              <div class="stat-label">Total Savings</div>
            </div>
          </div>
        </div>

        <!-- Orders List -->
        <div class="orders-section">
          <div class="section-header">
            <h2>Your Orders</h2>
            <span class="order-count">{{ orders.length }} order{{ orders.length !== 1 ? 's' : '' }}</span>
          </div>

          <!-- No Orders State -->
          <div v-if="orders.length === 0" class="no-orders">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
            </svg>
            <h3>No orders yet</h3>
            <p>Start shopping to see your order history here!</p>
            <router-link to="/" class="btn btn-primary">Browse Products</router-link>
          </div>

          <!-- Orders Grid -->
          <div v-else class="orders-grid">
            <div v-for="order in orders" :key="order.order_id" class="order-card">
              <div class="order-header">
                <div class="order-info">
                  <h3 class="order-number">Order #{{ order.order_id }}</h3>
                  <p class="order-date">{{ formatDate(order.order_date) }}</p>
                </div>
                <div class="order-total">
                  <span class="total-label">Total</span>
                  <span class="total-value">${{ formatCurrency(order.order_total) }}</span>
                </div>
              </div>

              <div class="order-store">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
                <span>{{ order.store_name }}, {{ order.store_location }}</span>
              </div>

              <div class="order-items">
                <div v-for="item in order.items" :key="item.order_item_id" class="order-item">
                  <div class="item-image">
                    <img v-if="item.image_url" :src="`/images/${item.image_url}`" :alt="item.product_name" />
                    <div v-else class="placeholder-image">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <polyline points="21 15 16 10 5 21"/>
                      </svg>
                    </div>
                  </div>
                  <div class="item-details">
                    <div class="item-name">{{ item.product_name }}</div>
                    <div class="item-sku">SKU: {{ item.sku }}</div>
                    <div class="item-price-row">
                      <span class="item-quantity">Qty: {{ item.quantity }}</span>
                      <span class="item-price">${{ formatCurrency(item.unit_price) }} each</span>
                    </div>
                    <div v-if="item.discount_amount > 0" class="item-discount">
                      💰 Saved ${{ formatCurrency(item.discount_amount) }} ({{ item.discount_percent }}% off)
                    </div>
                  </div>
                  <div class="item-total">
                    ${{ formatCurrency(item.total_amount) }}
                  </div>
                </div>
              </div>

              <div class="order-summary">
                <div class="summary-row">
                  <span>{{ order.total_items }} item{{ order.total_items !== 1 ? 's' : '' }}</span>
                  <span class="summary-total">Order Total: ${{ formatCurrency(order.order_total) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Back to Store Link -->
        <div class="back-link-container">
          <router-link to="/" class="btn btn-secondary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="19" y1="12" x2="5" y2="12"/>
              <polyline points="12 19 5 12 12 5"/>
            </svg>
            Back to Store
          </router-link>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="error" class="error-message">
        <p>{{ error }}</p>
        <button @click="loadOrders" class="btn btn-primary">Try Again</button>
      </div>
    </div>
  </div>
</template>

<script>
import { customerService } from '../services/customer';
import { authStore } from '../stores/auth';

export default {
  name: 'CustomerDashboard',
  data() {
    return {
      loading: true,
      error: null,
      orders: [],
      username: authStore.user?.username || 'Customer'
    };
  },
  computed: {
    orderStats() {
      if (this.orders.length === 0) {
        return {
          totalOrders: 0,
          totalItems: 0,
          totalSpent: 0,
          totalSavings: 0
        };
      }

      return {
        totalOrders: this.orders.length,
        totalItems: this.orders.reduce((sum, order) => sum + order.total_items, 0),
        totalSpent: this.orders.reduce((sum, order) => sum + order.order_total, 0),
        totalSavings: this.orders.reduce((sum, order) => {
          return sum + order.items.reduce((itemSum, item) => itemSum + item.discount_amount, 0);
        }, 0)
      };
    }
  },
  mounted() {
    this.loadOrders();
  },
  methods: {
    async loadOrders() {
      this.loading = true;
      this.error = null;

      try {
        const data = await customerService.getOrders();
        this.orders = data.orders || [];
      } catch (error) {
        console.error('Error loading orders:', error);
        this.error = 'Failed to load your orders. Please try again.';
      } finally {
        this.loading = false;
      }
    },
    formatCurrency(value) {
      return Number(value).toFixed(2);
    },
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
    }
  }
};
</script>

<style scoped>
.customer-dashboard {
  min-height: 100vh;
  background: #f8f9fa;
  padding: 2rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e9ecef;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.welcome-banner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 2.5rem;
  margin-bottom: 2rem;
  color: white;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.welcome-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.welcome-subtitle {
  font-size: 1.125rem;
  opacity: 0.95;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  display: flex;
  gap: 1rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon.orders {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stat-icon.items {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.stat-icon.spent {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.stat-icon.savings {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #718096;
  font-weight: 500;
}

.orders-section {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e9ecef;
}

.section-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a202c;
}

.order-count {
  background: #e9ecef;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
}

.no-orders {
  text-align: center;
  padding: 3rem 1rem;
  color: #718096;
}

.no-orders svg {
  opacity: 0.3;
  margin-bottom: 1rem;
}

.no-orders h3 {
  font-size: 1.5rem;
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.no-orders p {
  margin-bottom: 1.5rem;
}

.orders-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.order-card {
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 1.5rem;
  transition: box-shadow 0.2s;
}

.order-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e9ecef;
}

.order-number {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 0.25rem;
}

.order-date {
  font-size: 0.875rem;
  color: #718096;
}

.order-total {
  text-align: right;
}

.total-label {
  display: block;
  font-size: 0.75rem;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}

.total-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #667eea;
}

.order-store {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #495057;
}

.order-store svg {
  color: #667eea;
  flex-shrink: 0;
}

.order-items {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

.order-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.item-image {
  width: 80px;
  height: 80px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e9ecef;
  color: #adb5bd;
}

.item-details {
  flex: 1;
}

.item-name {
  font-weight: 600;
  color: #1a202c;
  margin-bottom: 0.25rem;
}

.item-sku {
  font-size: 0.75rem;
  color: #718096;
  margin-bottom: 0.5rem;
}

.item-price-row {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: #495057;
  margin-bottom: 0.25rem;
}

.item-discount {
  font-size: 0.875rem;
  color: #38a169;
  font-weight: 600;
}

.item-total {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1a202c;
  align-self: center;
}

.order-summary {
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  color: #495057;
}

.summary-total {
  font-size: 1rem;
  font-weight: 700;
  color: #1a202c;
}

.back-link-container {
  text-align: center;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s;
  border: none;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: white;
  color: #495057;
  border: 2px solid #e9ecef;
}

.btn-secondary:hover {
  background: #f8f9fa;
  border-color: #dee2e6;
}

.error-message {
  text-align: center;
  padding: 3rem;
  color: #e53e3e;
}

.error-message p {
  margin-bottom: 1rem;
}

@media (max-width: 768px) {
  .welcome-title {
    font-size: 1.5rem;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .order-header {
    flex-direction: column;
    gap: 1rem;
  }

  .order-total {
    text-align: left;
  }

  .order-item {
    flex-direction: column;
  }

  .item-image {
    width: 100%;
    height: 200px;
  }

  .item-total {
    align-self: flex-start;
  }
}
</style>
