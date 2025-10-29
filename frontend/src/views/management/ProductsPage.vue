<template>
  <div class="products-page">
    <div class="container">
      <div class="page-header">
        <div class="header-left">
          <h1>Products</h1>
          <p class="page-description">Manage product catalog and pricing</p>
        </div>
        <div class="header-right">
          <button class="btn btn-primary" @click="handleAddProduct">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Add Product
          </button>
        </div>
      </div>

      <!-- Coming in next message: Full products table -->
      <div class="coming-soon">
        <p>Products management interface with tables showing:</p>
        <ul>
          <li>Product catalog with SKUs</li>
          <li>Pricing and margins</li>
          <li>Supplier information</li>
          <li>Stock status</li>
          <li>CRUD operations</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProductsPage',
  methods: {
    handleAddProduct() {
      alert('Add Product form - Coming soon!');
    }
  }
};
</script>

<style scoped>
.products-page {
  padding-bottom: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.header-left h1 {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--primary-color);
}

.page-description {
  color: var(--secondary-color);
}

.header-right .btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.coming-soon {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
</style>
