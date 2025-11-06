<template>
  <div class="dashboard-page">
    <div class="container">
      <!-- Loading State -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <!-- Dashboard Content -->
      <div v-else>
        <!-- User Banner -->
        <div class="user-banner">
          <div class="banner-image" :style="{ backgroundImage: `url(${storeImage})` }">
            <div class="banner-overlay"></div>
          </div>
          <div class="banner-content">
            <div class="banner-info">
              <div class="banner-icon">
<vibe-icon name="home" size="32" filled></vibe-icon>
              </div>
              <div class="banner-text">
                <h2 class="banner-title">{{ storeName }}</h2>
                <p class="banner-subtitle">Logged in as <strong>{{ username }}</strong> • {{ userRole }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Stats Cards -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon revenue">
<vibe-icon name="money" size="24"></vibe-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">${{ formatNumber(stats.totalRevenue) }}</div>
              <div class="stat-label">Total Inventory Value</div>
              <div class="stat-change positive">+{{ stats.revenueChange }}% from last month</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon products">
              <vibe-icon name="box" size="24"></vibe-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.totalProducts }}</div>
              <div class="stat-label">Total Products</div>
              <div class="stat-info">Across all categories</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon suppliers">
<vibe-icon name="person-add" size="24"></vibe-icon>

            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.totalSuppliers }}</div>
              <div class="stat-label">Active Suppliers</div>
              <div class="stat-info">{{ Math.round(stats.totalSuppliers * 0.8) }} ESG compliant</div>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon stores">
<vibe-icon name="home" size="24"></vibe-icon>

            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.totalStores }}</div>
              <div class="stat-label">Popup Stores</div>
              <div class="stat-info">Across the US</div>
            </div>
          </div>
        </div>

        <!-- Alerts -->
        <div class="alerts-section">
          <div class="alert alert-warning">
<vibe-icon name="warning" size="24"></vibe-icon>

            <div>
              <strong>{{ stats.lowStockItems }} products</strong> are running low on stock
              <router-link to="/management/inventory" class="alert-link">View Inventory →</router-link>
            </div>
          </div>

          <div class="alert alert-info">
<vibe-icon name="info" size="24"></vibe-icon>
            <div>
              <strong>{{ stats.pendingOrders }} pending orders</strong> awaiting approval
            </div>
          </div>
        </div>

        <!-- Charts Row -->
        <div class="charts-row">
          <!-- Top Categories Chart -->
          <div class="chart-card">
            <h3 class="chart-title">Top Categories by Revenue</h3>
            <div class="category-chart">
              <div 
                v-for="category in stats.topCategories" 
                :key="category.name"
                class="category-bar"
              >
                <div class="category-info">
                  <span class="category-name">{{ category.name }}</span>
                  <span class="category-revenue">${{ formatNumber(category.revenue) }}</span>
                </div>
                <div class="bar-container">
                  <div class="bar-fill" :style="{ width: category.percentage + '%' }"></div>
                  <span class="bar-percentage">{{ category.percentage }}%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Weekly Insights (AI-Driven) -->
          <div class="chart-card insights-card">
            <div class="insights-header">
              <h3 class="chart-title">
<vibe-icon name="chat" size="24"></vibe-icon>
                Weekly Insights
              </h3>
              <span class="ai-badge"><vibe-icon name="sparkle"></vibe-icon>
 AI Generated</span>
            </div>
            
            <div class="insights-content" v-if="!loadingInsights">
              <p class="insights-summary">
                {{ weeklyInsights.summary }}
              </p>
              
              <div class="insights-list">
                <div 
                  v-for="(insight, index) in weeklyInsights.insights" 
                  :key="index"
                  class="insight-item"
                  :class="'insight-' + insight.type"
                >
                  <div class="insight-icon">
                    <vibe-icon v-if="insight.type === 'success'" name="checkmark" size="24"></vibe-icon>
                    <vibe-icon v-else-if="insight.type === 'warning'" name="warning" size="24"></vibe-icon>
                    <vibe-icon v-else name="info" size="24"></vibe-icon>
                  </div>
                  <div class="insight-text">
                    <strong>{{ insight.title }}</strong>
                    <p>{{ insight.description }}</p>
                  </div>
                  <button
                    v-if="insight.action"
                    class="insight-action-btn"
                    @click="handleInsightAction(insight.action)"
                  >
                    {{ insight.action.label }}
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M6 3L11 8L6 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Loading State -->
            <div class="insights-content" v-else>
              <div class="insights-loading">
                <div class="spinner"></div>
                <p>Loading AI insights...</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="quick-actions">
          <h3>Quick Actions</h3>
          <div class="actions-grid">
            <router-link to="/management/suppliers" class="action-card">
              <div class="action-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="8.5" cy="7" r="4"/>
                  <path d="M20 8v6M23 11h-6"/>
                </svg>
              </div>
              <div class="action-content">
                <h4>Add Supplier</h4>
                <p>Register a new supplier</p>
              </div>
            </router-link>

            <router-link to="/management/inventory" class="action-card">
              <div class="action-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                </svg>
              </div>
              <div class="action-content">
                <h4>Update Inventory</h4>
                <p>Manage stock levels</p>
              </div>
            </router-link>

            <router-link to="/management/products" class="action-card">
              <div class="action-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
                  <line x1="3" y1="6" x2="21" y2="6"/>
                </svg>
              </div>
              <div class="action-content">
                <h4>Add Product</h4>
                <p>Create new product listing</p>
              </div>
            </router-link>

            <router-link to="/management/policies" class="action-card">
              <div class="action-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
              </div>
              <div class="action-content">
                <h4>Review Policies</h4>
                <p>View company policies</p>
              </div>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { managementService } from '../../services/management';
import { authStore } from '../../stores/auth';
import { useRouter } from 'vue-router';

export default {
  name: 'DashboardPage',
  setup() {
    const router = useRouter();
    return { router };
  },
  data() {
    return {
      loading: false,
      loadingInsights: false,
      stats: {
        totalRevenue: 0,
        totalProducts: 0,
        totalSuppliers: 0,
        totalStores: 0,
        lowStockItems: 0,
        pendingOrders: 0,
        revenueChange: 0,
        topCategories: [],
        recentActivity: []
      },
      weeklyInsights: {
        summary: '',
        insights: []
      }
    };
  },
  computed: {
    username() {
      return authStore.user?.username || 'User';
    },
    storeName() {
      return authStore.user?.store_name || (authStore.user?.role === 'admin' ? 'All Stores' : 'Store');
    },
    userRole() {
      const role = authStore.user?.role || '';
      if (role === 'admin') return 'Administrator';
      if (role === 'store_manager') return 'Store Manager';
      return role;
    },
    storeImage() {
      // Map store names to image files
      const storeName = authStore.user?.store_name;
      if (!storeName) return '/images/store.png';
      
      // Convert store name to image filename
      const imageMap = {
        'Popup NYC Times Square': '/images/store_nyc_times_square.png',
        'Popup SF Union Square': '/images/store.png', // Use default for SF
        'Popup Pike Place': '/images/store_pike_place.png',
        'Popup Kirkland Waterfront': '/images/store_kirkland_waterfront.png',
        'Popup Spokane Pavilion': '/images/store_spokane_pavilion.png',
        'Popup Everett Station': '/images/store_everett_station.png'
      };
      
      return imageMap[storeName] || '/images/store.png';
    }
  },
  async mounted() {
    await Promise.all([
      this.loadDashboard(),
      this.loadWeeklyInsights()
    ]);
  },
  methods: {
    async loadDashboard() {
      this.loading = true;
      try {
        this.stats = await managementService.getDashboardStats();
      } catch (error) {
        console.error('Error loading dashboard:', error);
      } finally {
        this.loading = false;
      }
    },
    async loadWeeklyInsights() {
      this.loadingInsights = true;
      try {
        this.weeklyInsights = await managementService.getWeeklyInsights();
      } catch (error) {
        console.error('Error loading weekly insights:', error);
        this.weeklyInsights = {
          summary: 'Unable to load insights at this time.',
          insights: []
        };
      } finally {
        this.loadingInsights = false;
      }
    },
    formatNumber(num) {
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(num);
    },
    handleInsightAction(action) {
      if (!action) return;
      
      switch (action.type) {
        case 'product-search':
          // Navigate to products page with search query
          this.router.push({
            path: '/management/products',
            query: { search: action.query }
          });
          break;
        case 'navigation':
          // Direct navigation to specified path
          this.router.push(action.path);
          break;
        default:
          console.warn('Unknown action type:', action.type);
      }
    }
  }
};
</script>

<style scoped>
.dashboard-page {
  padding-bottom: 2rem;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--primary-color);
}

.page-description {
  color: var(--secondary-color);
  font-size: 1rem;
}

/* User Banner */
.user-banner {
  position: relative;
  background: white;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.banner-image {
  height: 180px;
  background-size: cover;
  background-position: center;
  position: relative;
}

.banner-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.2), rgba(0, 0, 0, 0.6));
}

.banner-content {
  padding: 1.5rem 2rem;
  background: linear-gradient(135deg, #183D4c 0%, #9EC9D9 100%);
  color: white;
}

.banner-info {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.banner-icon {
  width: 60px;
  height: 60px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  backdrop-filter: blur(10px);
}

.banner-text {
  flex: 1;
}

.banner-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
  color: white;
}

.banner-subtitle {
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
}

.banner-subtitle strong {
  font-weight: 600;
  color: white;
}

/* Stats Grid */
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
  display: flex;
  gap: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon.revenue { background: #e8f5e9; color: #388e3c; }
.stat-icon.products { background: #f3e5f5; color: #7b1fa2; }
.stat-icon.suppliers { background: #e3f2fd; color: #1976d2; }
.stat-icon.stores { background: #fff3e0; color: #f57c00; }

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--accent-color);
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.stat-change {
  font-size: 0.75rem;
  font-weight: 600;
}

.stat-change.positive { color: #388e3c; }

.stat-info {
  font-size: 0.75rem;
  color: var(--border-color);
}

/* Alerts */
.alerts-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.alert {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  font-size: 0.9rem;
}

.alert svg {
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.alert-warning {
  background: #fff3cd;
  border: 1px solid #ffc107;
  color: #856404;
}

.alert-info {
  background: #d1ecf1;
  border: 1px solid #17a2b8;
  color: #0c5460;
}

.alert-link {
  color: inherit;
  font-weight: 600;
  text-decoration: underline;
  margin-left: 0.5rem;
}

/* Charts */
.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.chart-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.chart-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Category Chart */
.category-chart {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.category-bar {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.category-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.category-name {
  font-weight: 600;
  color: var(--text-color);
}

.category-revenue {
  color: var(--text-color);
  font-weight: 500;
}

.bar-container {
  position: relative;
  height: 24px;
  background: var(--hover-color);
  border-radius: 12px;
  overflow: hidden;
}

.bar-fill {
  position: absolute;
  height: 100%;
  background: linear-gradient(90deg, #183D4c, #0a0c0c);
  border-radius: 12px;
  transition: width 0.6s ease;
}

.bar-percentage {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color);
}

/* Weekly Insights */
.insights-card {
  /* background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); */
  border: 2px solid #e1e8ed;
}

.insights-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  color: var(--accent-color);
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 20px;
  border: 1px solid var(--accent-color);
  margin-top: -18px;
}

.insights-content {
  background: white;
  border-radius: 8px;
}

.insights-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  gap: 1rem;
}

.insights-loading .spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.insights-loading p {
  color: var(--secondary-color);
  font-size: 0.95rem;
  margin: 0;
}

.insights-summary {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--text-color);
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  /* border-bottom: 2px solid var(--border-color); */
}

.insights-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.insight-item {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  gap: 0.875rem;
  padding: 1rem;
  border-radius: 8px;
  border-left: 3px solid;
  background: var(--hover-color);
  transition: transform 0.2s, box-shadow 0.2s;
}

/* .insight-item:hover {
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
} */

.insight-item.insight-success {
  border-left-color: var(--success-color);
  background: #e8f5e9;
}

.insight-item.insight-warning {
  border-left-color: var(--warning-color);
  background: #fff3e0;
}

.insight-item.insight-info {
  border-left-color: var(--primary-color);
  background: #e3f2fd;
}

.insight-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  grid-row: 1 / 2;
  align-self: start;
}

.insight-success .insight-icon {
  color: var(--success-color);
}

.insight-warning .insight-icon {
  color: var(--warning-color);
}

.insight-info .insight-icon {
  color: var(--primary-color);
}

.insight-text {
  grid-column: 2 / 3;
  grid-row: 1 / 2;
}

.insight-text strong {
  display: block;
  font-size: 0.925rem;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 0.375rem;
}

.insight-text p {
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--text-color);
  margin: 0;
}

.insight-action-btn {
  grid-column: 2 / 3;
  grid-row: 2 / 3;
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  margin-top: 0.5rem;
  background: white;
  border: 2px solid currentColor;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  color: inherit;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.insight-success .insight-action-btn {
  color: var(--success-color);
  border-color: var(--success-color);
}

.insight-success .insight-action-btn:hover {
  background: var(--success-color);
  color: white;
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(46, 125, 50, 0.3);
}

.insight-warning .insight-action-btn {
  color: var(--warning-color);
  border-color: var(--warning-color);
}

.insight-warning .insight-action-btn:hover {
  background: var(--warning-color);
  color: white;
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(230, 81, 0, 0.3);
}

.insight-info .insight-action-btn {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.insight-info .insight-action-btn:hover {
  background: var(--primary-color);
  color: white;
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(21, 101, 192, 0.3);
}

/* Quick Actions */
.quick-actions {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.quick-actions h3 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: var(--primary-color);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.2s;
}

.action-card:hover {
  border-color: var(--accent-color);
  background: var(--hover-color);
}

.action-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: var(--hover-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-color);
  flex-shrink: 0;
}

.action-content h4 {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--text-color);
}

.action-content p {
  font-size: 0.75rem;
  color: var(--text-color);
  margin: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .alerts-section {
    flex-direction: column;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }

  .actions-grid {
    grid-template-columns: 1fr;
  }
}
</style>
