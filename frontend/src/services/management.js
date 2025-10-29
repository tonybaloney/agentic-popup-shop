import axios from 'axios';
import { authStore } from '../stores/auth';

const managementApi = axios.create({
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add request interceptor to include auth token
managementApi.interceptors.request.use(
  (config) => {
    const token = authStore.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle 401 errors
managementApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token is invalid or expired, logout user
      authStore.logout();
      // Redirect to login page
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const managementService = {
  // Dashboard stats
  async getDashboardStats() {
    try {
      // Get top categories from the real API
      const topCategoriesResponse = await managementApi.get('/api/management/dashboard/top-categories?limit=5');
      const topCategories = topCategoriesResponse.data.categories;

      // Get mock data for other stats (will be replaced with real data later)
      const mockStats = this.getMockDashboardStats();

      // Merge real and mock data
      return {
        ...mockStats,
        topCategories: topCategories
      };
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      return this.getMockDashboardStats();
    }
  },

  // Suppliers
  async getSuppliers() {
    try {
      const response = await managementApi.get('/api/management/suppliers');
      // API returns {suppliers: [...], total: ...}
      return response.data.suppliers || response.data;
    } catch (error) {
      console.error('Error fetching suppliers:', error);
      return this.getMockSuppliers();
    }
  },

  // Inventory
  async getInventory(params = {}) {
    try {
      const response = await managementApi.get('/api/management/inventory', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching inventory:', error);
      return this.getMockInventory();
    }
  },

  // Products
  async getProducts(params = {}) {
    try {
      const response = await managementApi.get('/api/management/products', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching products:', error);
      return this.getMockProducts();
    }
  },

  // Policies
  async getPolicies() {
    try {
      const response = await managementApi.get('/api/management/policies');
      return response.data;
    } catch (error) {
      console.error('Error fetching policies:', error);
      return this.getMockPolicies();
    }
  },

  // Weekly Insights
  async getWeeklyInsights() {
    try {
      const response = await managementApi.get('/api/management/insights');
      return response.data;
    } catch (error) {
      console.error('Error fetching weekly insights:', error);
      // Return empty insights on error
      return {
        summary: "NYC Times Square store performance remains strong this week with foot traffic up 12%. Weather forecasts indicate a significant cold snap arriving next week (temperatures dropping to 28°F/-2°C). This presents an immediate opportunity to capitalize on cold-weather accessory demand, particularly beanies and winter hats which saw 340% increase during last year's similar weather event.",
        insights: [
            {
              type: "warning",
              title: "Cold Snap Alert - Stock Winter Accessories",
              description: "Weather forecast shows temperatures dropping to 28°F starting Monday. Current beanie inventory: 47 units. Recommend immediate order of 200+ units across popular styles. Last year's cold snap generated $8,400 in beanie sales over 3 days.",
              action: {
                label: "View Beanies",
                type: "product-search",
                query: "beanie"
              }
            },
            {
              type: "success",
              title: "Tourist Season Performance",
              description: "Times Square location seeing 18% increase in tourist traffic vs last month. Branded merchandise and gift items up 24% week-over-week."
            },
            {
              type: "info",
              title: "Peak Hours Optimization",
              description: "Busiest hours: 2-6pm weekdays, 11am-8pm weekends. Consider adjusting staff schedules to maximize customer service during these windows."
            },
            {
              type: "success",
              title: "Local Partnership Opportunity",
              description: "NYC-themed merchandise performing exceptionally well (32% of accessory sales). Consider expanding local artist collaborations for holiday season."
            }
          ]
      };
    }
  },

  // Mock data methods
  getMockDashboardStats() {
    return {
      totalRevenue: 249456.85,
      totalProducts: 145,
      totalSuppliers: 20,
      totalStores: 7,
      lowStockItems: 12,
      pendingOrders: 8,
      revenueChange: 12.5,
      inventoryValue: 249456.85,
      topCategories: [
        { name: 'Footwear', revenue: 65000, percentage: 26 },
        { name: 'Outerwear', revenue: 55000, percentage: 22 },
        { name: 'Apparel - Tops', revenue: 48000, percentage: 19 },
        { name: 'Apparel - Bottoms', revenue: 45000, percentage: 18 },
        { name: 'Accessories', revenue: 36456, percentage: 15 }
      ],
      recentActivity: [
        { id: 1, action: 'Low stock alert', item: 'Classic White Sneakers', store: 'Pike Place', time: '2 hours ago' },
        { id: 2, action: 'New supplier approved', item: 'Urban Threads Wholesale', time: '5 hours ago' },
        { id: 3, action: 'Inventory updated', item: 'Bomber Jacket', store: 'Bellevue Square', time: '1 day ago' }
      ]
    };
  },

  getMockSuppliers() {
    return [
      {
        id: 1,
        name: 'Urban Threads Wholesale',
        code: 'SUP001',
        location: 'Seattle, WA',
        contact: 'michael.chen@urbanthreads.com',
        phone: '(206) 555-0101',
        rating: 4.8,
        esg_compliant: true,
        approved: true,
        preferred: true,
        categories: ['Apparel - Tops', 'Accessories'],
        lead_time: 12,
        payment_terms: 'Net 30',
        min_order: 2500,
        bulk_discount: 7.17
      },
      {
        id: 2,
        name: 'Elite Fashion Distributors',
        code: 'SUP002',
        location: 'Bellevue, WA',
        contact: 'sarah.j@elitefashion.com',
        phone: '(425) 555-0102',
        rating: 4.9,
        esg_compliant: true,
        approved: true,
        preferred: true,
        categories: ['Apparel - Tops', 'Apparel - Bottoms'],
        lead_time: 10,
        payment_terms: 'Net 30',
        min_order: 5000,
        bulk_discount: 8.5
      },
      {
        id: 3,
        name: 'Pacific Apparel Group',
        code: 'SUP003',
        location: 'Tacoma, WA',
        contact: 'james@pacificapparel.com',
        phone: '(253) 555-0103',
        rating: 4.7,
        esg_compliant: true,
        approved: true,
        preferred: true,
        categories: ['Apparel - Tops'],
        lead_time: 14,
        payment_terms: 'Net 45',
        min_order: 3000,
        bulk_discount: 6.8
      }
    ];
  },

  getMockInventory() {
    return [
      {
        id: 1,
        productName: 'Classic White Sneakers',
        sku: 'FOOT-SNK-001',
        category: 'Footwear',
        stores: [
          { name: 'Pike Place', stock: 8, status: 'low' },
          { name: 'Bellevue Square', stock: 15, status: 'ok' },
          { name: 'Kirkland', stock: 12, status: 'ok' }
        ],
        totalStock: 35,
        unitPrice: 79.99,
        totalValue: 2799.65,
        reorderPoint: 20,
        supplier: 'Athletic Footwear Network'
      },
      {
        id: 2,
        productName: 'Laptop Commuter Backpack',
        sku: 'ACC-BAG-002',
        category: 'Accessories',
        stores: [
          { name: 'Pike Place', stock: 12, status: 'ok' },
          { name: 'Bellevue Square', stock: 19, status: 'ok' },
          { name: 'Kirkland', stock: 8, status: 'low' }
        ],
        totalStock: 39,
        unitPrice: 82.07,
        totalValue: 3200.73,
        reorderPoint: 15,
        supplier: 'Bag & Luggage Distributors'
      }
    ];
  },

  getMockProducts() {
    return {
      products: [
        {
          product_id: 1,
          sku: 'FOOT-SNK-001',
          name: 'Classic White Sneakers',
          description: 'Comfortable classic white sneakers',
          category: 'Footwear',
          type: 'Sneakers',
          base_price: 79.99,
          cost: 45.00,
          margin: 43.7,
          discontinued: false,
          supplier_id: 1,
          supplier_name: 'Athletic Footwear Network',
          supplier_code: 'SUP001',
          lead_time: 7,
          total_stock: 35,
          store_count: 3,
          stock_value: 1575.00,
          retail_value: 2799.65,
          image_url: '/images/products/sneakers-white.jpg'
        },
        {
          product_id: 2,
          sku: 'ACC-BAG-002',
          name: 'Laptop Commuter Backpack',
          description: 'Professional laptop backpack',
          category: 'Accessories',
          type: 'Backpacks & Bags',
          base_price: 82.07,
          cost: 48.50,
          margin: 40.9,
          discontinued: false,
          supplier_id: 2,
          supplier_name: 'Bag & Luggage Distributors',
          supplier_code: 'SUP002',
          lead_time: 10,
          total_stock: 39,
          store_count: 3,
          stock_value: 1891.50,
          retail_value: 3200.73,
          image_url: '/images/products/backpack-laptop.jpg'
        }
      ],
      pagination: {
        total: 2,
        limit: 100,
        offset: 0,
        has_more: false
      }
    };
  },

  getMockPolicies() {
    return [
      {
        id: 1,
        name: 'Procurement Policy',
        type: 'Procurement',
        department: 'Procurement',
        content: 'All purchases over $5,000 require manager approval. Competitive bidding required for orders over $25,000.',
        minThreshold: 5000,
        approvalRequired: true,
        effectiveDate: '2025-01-01',
        status: 'active'
      },
      {
        id: 2,
        name: 'Budget Authorization',
        type: 'Budget Authorization',
        department: 'Finance',
        content: 'Spending limits: Manager $50K, Director $250K, Executive $1M+',
        minThreshold: null,
        approvalRequired: true,
        effectiveDate: '2025-01-01',
        status: 'active'
      },
      {
        id: 3,
        name: 'Vendor Approval',
        type: 'Vendor Approval',
        department: 'Procurement',
        content: 'All new vendors require approval and background check completion.',
        minThreshold: null,
        approvalRequired: true,
        effectiveDate: '2025-01-01',
        status: 'active'
      },
      {
        id: 4,
        name: 'Order Processing Policy',
        type: 'Order Processing',
        department: 'Operations',
        content: 'Orders processed within 24 hours. Rush orders require $50 fee and manager approval.',
        minThreshold: null,
        approvalRequired: false,
        effectiveDate: '2025-01-01',
        status: 'active'
      }
    ];
  }
};

export default managementApi;
