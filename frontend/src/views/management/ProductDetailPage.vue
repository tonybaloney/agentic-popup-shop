<template>
  <div class="product-detail-page">
    <div class="container">
      <!-- Loading State -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>Loading product details...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">❌</div>
        <h2>Product Not Found</h2>
        <p>{{ error }}</p>
        <router-link to="/management/products" class="btn btn-primary">
          Back to Products
        </router-link>
      </div>

      <!-- Product Details -->
      <div v-else-if="product" class="product-content">
        <!-- Header with Back Button -->
        <div class="page-header">
          <router-link to="/management/inventory" class="back-link">
            <i class="bi bi-arrow-left"></i> Back to Inventory
          </router-link>
          <div class="header-actions">
            <button class="btn btn-secondary" @click="handleEdit">
              <i class="bi bi-pencil"></i> Edit Product
            </button>
          </div>
        </div>

        <!-- Main Content Grid -->
        <div class="product-grid">
          <!-- Left Column: Image and Basic Info -->
          <div class="product-image-section">
            <div class="image-container">
              <img 
                :src="productImageUrl" 
                :alt="product.product_name" 
                class="product-image"
                @error="handleImageError"
              />
            </div>
            
            <div class="product-status">
              <span v-if="product.discontinued" class="status-badge discontinued">
                <i class="bi bi-x-circle"></i> Discontinued
              </span>
              <span v-else class="status-badge active">
                <i class="bi bi-check-circle"></i> Active
              </span>
            </div>
          </div>

          <!-- Right Column: Details -->
          <div class="product-info-section">
            <div class="product-header">
              <h1>{{ product.product_name }}</h1>
              <div class="product-meta">
                <span class="sku">
                  <i class="bi bi-upc-scan"></i>
                  SKU: {{ product.sku }}
                </span>
                <span class="category">
                  <i class="bi bi-tag"></i>
                  {{ product.category_name }}
                </span>
                <span class="type">
                  <i class="bi bi-box"></i>
                  {{ product.type_name }}
                </span>
              </div>
            </div>

            <!-- Description -->
            <div v-if="product.product_description" class="product-description">
              <h3>Description</h3>
              <p>{{ product.product_description }}</p>
            </div>

            <!-- Pricing Information -->
            <div class="pricing-grid">
              <div class="price-card">
                <div class="price-label">Retail Price</div>
                <div class="price-value">${{ product.unit_price.toFixed(2) }}</div>
              </div>
              <div class="price-card">
                <div class="price-label">Cost</div>
                <div class="price-value">${{ product.cost.toFixed(2) }}</div>
              </div>
              <div class="price-card">
                <div class="price-label">Margin</div>
                <div class="price-value">{{ product.gross_margin_percent.toFixed(1) }}%</div>
              </div>
              <div class="price-card">
                <div class="price-label">Profit</div>
                <div class="price-value profit">${{ profit.toFixed(2) }}</div>
              </div>
            </div>

            <!-- Supplier Information -->
            <div v-if="product.supplier_name" class="supplier-info">
              <h3>
                <i class="bi bi-truck"></i>
                Supplier Information
              </h3>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">Supplier Name:</span>
                  <span class="info-value">{{ product.supplier_name }}</span>
                </div>
              </div>
            </div>

            <!-- Inventory Summary -->
            <div class="inventory-summary">
              <h3>
                <i class="bi bi-box-seam"></i>
                Inventory Levels
              </h3>
              <div v-if="inventoryLoading" class="loading-inline">
                <div class="spinner-small"></div>
                Loading inventory...
              </div>
              <div v-else-if="inventoryData.length > 0" class="inventory-table-container">
                <table class="inventory-table">
                  <thead>
                    <tr>
                      <th>Store</th>
                      <th>Location</th>
                      <th>Stock Level</th>
                      <th>Stock Value</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="inv in inventoryData" :key="inv.storeId" 
                        :class="{ 'low-stock-row': inv.isLowStock }">
                      <td class="store-name">{{ inv.store_name }}</td>
                      <td class="store-location">{{ inv.store_location }}</td>
                      <td class="stock-level">
                        <strong>{{ inv.stock_level }}</strong> units
                      </td>
                      <td class="value-cell">${{ (inv.stock_level * product.cost).toFixed(2) }}</td>
                      <td>
                        <span v-if="inv.isLowStock" class="status-badge status-low">
                          ⚠️ Low Stock
                        </span>
                        <span v-else class="status-badge status-good">
                          ✓ Good
                        </span>
                      </td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colspan="2" class="total-label"><strong>Total Inventory:</strong></td>
                      <td class="stock-level"><strong>{{ totalStock }}</strong> units</td>
                      <td class="value-cell"><strong>${{ totalValue.toFixed(2) }}</strong></td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <div v-else class="no-inventory">
                <i class="bi bi-inbox"></i>
                <p>No inventory data available</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { apiClient } from '../../config/api'

const route = useRoute()
const sku = computed(() => route.params.sku)

// State
const product = ref(null)
const loading = ref(true)
const error = ref(null)
const inventoryData = ref([])
const inventoryLoading = ref(false)

// Computed properties
const productImageUrl = computed(() => {
  if (product.value && product.value.image_url) {
    return `/images/${product.value.image_url}`
  }
  return `/images/${sku.value}.png`
})

const profit = computed(() => {
  if (!product.value) return 0
  return product.value.unit_price - product.value.cost
})

const totalStock = computed(() => {
  return inventoryData.value.reduce((sum, inv) => sum + inv.stockLevel, 0)
})

const totalValue = computed(() => {
  if (!product.value) return 0
  return totalStock.value * product.value.cost
})

// Fetch product details
const fetchProduct = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await apiClient.get(`/api/products/sku/${sku.value}`)
    product.value = response.data
    
    // Fetch inventory data
    await fetchInventory()
  } catch (err) {
    console.error('Failed to fetch product:', err)
    if (err.response && err.response.status === 404) {
      error.value = `Product with SKU "${sku.value}" not found`
    } else {
      error.value = 'Failed to load product details. Please try again later.'
    }
  } finally {
    loading.value = false
  }
}

// Fetch inventory levels for this product
const fetchInventory = async () => {
  if (!product.value) return
  
  inventoryLoading.value = true
  
  try {
    // Fetch inventory filtered by product_id
    const response = await apiClient.get('/api/management/inventory', {
      params: {
        product_id: product.value.product_id,
        limit: 100
      }
    })
    
    if (response.data && response.data.inventory) {
      inventoryData.value = response.data.inventory
      console.log(`Found ${inventoryData.value.length} inventory records for product ${product.value.product_id}`)
    }
  } catch (err) {
    console.error('Failed to fetch inventory:', err)
    // Don't show error for inventory, just leave it empty
  } finally {
    inventoryLoading.value = false
  }
}

// Handle image error
const handleImageError = (event) => {
  event.target.src = '/images/placeholder.png'
  event.target.onerror = null
}

// Handle edit button
const handleEdit = () => {
  alert('Product editing coming soon!')
}

// Lifecycle
onMounted(() => {
  fetchProduct()
})
</script>

<style scoped>
.product-detail-page {
  padding-bottom: 2rem;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Loading & Error States */
.loading {
  text-align: center;
  padding: 4rem 0;
}

.spinner {
  width: 3rem;
  height: 3rem;
  border: 4px solid #e9ecef;
  border-top-color: #0d6efd;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.spinner-small {
  width: 1.5rem;
  height: 1.5rem;
  border: 3px solid #e9ecef;
  border-top-color: #0d6efd;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  display: inline-block;
  vertical-align: middle;
  margin-right: 0.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.error-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.error-state h2 {
  color: #dc3545;
  margin-bottom: 1rem;
}

.error-state p {
  color: #6c757d;
  margin-bottom: 2rem;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: #6c757d;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.back-link:hover {
  color: #495057;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}

.btn-primary {
  background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(13, 110, 253, 0.3);
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

/* Product Grid */
.product-grid {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 2rem;
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* Image Section */
.product-image-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.image-container {
  background: #f8f9fa;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #dee2e6;
}

.product-image {
  width: 100%;
  height: auto;
  display: block;
}

.product-status {
  text-align: center;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.9rem;
}

.status-badge.active {
  background: #d1f4e0;
  color: #0f5132;
}

.status-badge.discontinued {
  background: #f8d7da;
  color: #842029;
}

.status-badge.status-low {
  background: #fff3cd;
  color: #856404;
  font-size: 0.85rem;
}

.status-badge.status-good {
  background: #d1f4e0;
  color: #0f5132;
  font-size: 0.85rem;
}

/* Info Section */
.product-info-section {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.product-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #212529;
  margin-bottom: 1rem;
}

.product-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  color: #6c757d;
  font-size: 0.95rem;
}

.product-meta span {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.product-meta i {
  color: #0d6efd;
}

.sku {
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

/* Description */
.product-description h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: #495057;
}

.product-description p {
  color: #6c757d;
  line-height: 1.6;
}

/* Pricing Grid */
.pricing-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.price-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.25rem;
  border: 1px solid #dee2e6;
}

.price-label {
  font-size: 0.85rem;
  color: #6c757d;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.price-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #212529;
}

.price-value.profit {
  color: #28a745;
}

/* Supplier Info */
.supplier-info h3,
.inventory-summary h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #495057;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.supplier-info h3 i,
.inventory-summary h3 i {
  color: #0d6efd;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-label {
  font-size: 0.85rem;
  color: #6c757d;
  font-weight: 500;
}

.info-value {
  font-size: 1rem;
  color: #212529;
  font-weight: 600;
}

/* Inventory Table */
.inventory-table-container {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.inventory-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.inventory-table thead {
  background: #f8f9fa;
  border-bottom: 2px solid #dee2e6;
}

.inventory-table th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-weight: 600;
  color: #495057;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.inventory-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e9ecef;
  font-size: 0.9rem;
}

.inventory-table tbody tr:hover {
  background: #f8f9fa;
}

.inventory-table tbody tr.low-stock-row {
  background: #fff3cd;
}

.store-name {
  font-weight: 600;
  color: #212529;
}

.store-location {
  color: #6c757d;
  font-size: 0.85rem;
}

.stock-level {
  text-align: center;
}

.value-cell {
  text-align: right;
  font-weight: 600;
  color: #28a745;
}

.inventory-table tfoot {
  background: #f8f9fa;
  border-top: 2px solid #dee2e6;
  font-weight: 700;
}

.inventory-table tfoot td {
  padding: 1rem;
}

.total-label {
  text-align: right;
}

.loading-inline {
  padding: 2rem;
  text-align: center;
  color: #6c757d;
}

.no-inventory {
  padding: 3rem;
  text-align: center;
  color: #6c757d;
}

.no-inventory i {
  font-size: 3rem;
  display: block;
  margin-bottom: 1rem;
  opacity: 0.5;
}

/* Responsive */
@media (max-width: 1024px) {
  .product-grid {
    grid-template-columns: 1fr;
  }

  .pricing-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .pricing-grid {
    grid-template-columns: 1fr;
  }

  .product-header h1 {
    font-size: 1.5rem;
  }
}
</style>
