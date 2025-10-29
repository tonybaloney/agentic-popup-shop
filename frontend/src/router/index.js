import { createRouter, createWebHistory } from 'vue-router';
import HomePage from '../views/HomePage.vue';
import CategoryPage from '../views/CategoryPage.vue';
import LoginPage from '../views/LoginPage.vue';
import ManagementLayout from '../views/ManagementLayout.vue';
import { authStore } from '../stores/auth';

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomePage
  },
  {
    path: '/category/:category',
    name: 'Category',
    component: CategoryPage
  },
  {
    path: '/category/:category/:subcategory',
    name: 'Subcategory',
    component: CategoryPage
  },
  {
    path: '/stores',
    name: 'Stores',
    component: () => import('../views/StoresPage.vue')
  },
  {
    path: '/product/:id',
    name: 'Product',
    component: () => import('../views/ProductPage.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginPage
  },
  {
    path: '/management',
    component: ManagementLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Management',
        component: () => import('../views/management/DashboardPage.vue')
      },
      {
        path: 'suppliers',
        name: 'Suppliers',
        component: () => import('../views/management/SuppliersPage.vue')
      },
      {
        path: 'inventory',
        name: 'Inventory',
        component: () => import('../views/management/InventoryPage.vue')
      },
      {
        path: 'products',
        name: 'Products',
        component: () => import('../views/management/ProductsPage.vue')
      },
      {
        path: 'products/:sku',
        name: 'ProductDetail',
        component: () => import('../views/management/ProductDetailPage.vue')
      },
      {
        path: 'policies',
        name: 'Policies',
        component: () => import('../views/management/PoliciesPage.vue')
      },
      {
        path: 'ai-agent',
        name: 'AIAgent',
        component: () => import('../views/management/AIAgentPage.vue')
      }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    } else {
      return { top: 0 };
    }
  }
});

// Navigation guard
router.beforeEach((to, from, next) => {
  // Check auth on page load
  authStore.checkAuth();
  
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.isAuthenticated) {
      next('/login');
    } else {
      next();
    }
  } else {
    next();
  }
});

export default router;
