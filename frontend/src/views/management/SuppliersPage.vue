<template>
  <div class="suppliers-page">
    <div class="container">
      <div class="page-header">
        <div class="header-left">
          <h1>Suppliers</h1>
          <p class="page-description">Manage supplier relationships and contracts</p>
        </div>
        <div class="header-right">
          <button class="btn btn-primary" @click="handleAddSupplier">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Add Supplier
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <!-- Suppliers List -->
      <div v-else class="suppliers-container">
        <div class="suppliers-grid">
          <div v-for="supplier in suppliers" :key="supplier.id" class="supplier-card">
            <div class="supplier-header">
              <div class="supplier-title">
                <h3>{{ supplier.name }}</h3>
                <span class="supplier-code">{{ supplier.code }}</span>
              </div>
              <div class="supplier-badges">
                <span v-if="supplier.preferred" class="badge badge-preferred">Preferred</span>
                <span v-if="supplier.esgCompliant" class="badge badge-esg">ESG</span>
                <span class="badge badge-approved">Approved</span>
              </div>
            </div>

            <div class="supplier-details">
              <div class="detail-row">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
                <span>{{ supplier.location }}</span>
              </div>
              <div class="detail-row">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                  <polyline points="22,6 12,13 2,6"/>
                </svg>
                <span>{{ supplier.contact }}</span>
              </div>
              <div class="detail-row">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
                </svg>
                <span>{{ supplier.phone }}</span>
              </div>
            </div>

            <div class="supplier-metrics">
              <div class="metric">
                <div class="metric-label">Rating</div>
                <div class="metric-value">
                  ⭐ {{ supplier.rating.toFixed(1) }}
                </div>
              </div>
              <div class="metric">
                <div class="metric-label">Lead Time</div>
                <div class="metric-value">{{ supplier.lead_time }} days</div>
              </div>
              <div class="metric">
                <div class="metric-label">Bulk Discount</div>
                <div class="metric-value">{{ supplier.bulk_discount }}%</div>
              </div>
            </div>

            <div class="supplier-info">
              <div class="info-item">
                <strong>Categories:</strong> {{ supplier.categories.join(', ') }}
              </div>
              <div class="info-item">
                <strong>Payment:</strong> {{ supplier.payment_terms }}
              </div>
              <div class="info-item">
                <strong>Min Order:</strong> ${{ formatNumber(supplier.min_order) }}
              </div>
            </div>

            <div class="supplier-actions">
              <button class="btn-action btn-view" @click="handleViewSupplier(supplier)">
                View Details
              </button>
              <button class="btn-action btn-edit" @click="handleEditSupplier(supplier)">
                Edit
              </button>
              <button class="btn-action btn-contact" @click="handleContactSupplier(supplier)">
                Contact
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { managementService } from '../../services/management';

export default {
  name: 'SuppliersPage',
  data() {
    return {
      loading: false,
      suppliers: []
    };
  },
  async mounted() {
    await this.loadSuppliers();
  },
  methods: {
    async loadSuppliers() {
      this.loading = true;
      try {
        this.suppliers = await managementService.getSuppliers();
      } catch (error) {
        console.error('Error loading suppliers:', error);
      } finally {
        this.loading = false;
      }
    },
    formatNumber(num) {
      return new Intl.NumberFormat('en-US').format(num);
    },
    handleAddSupplier() {
      alert('Add Supplier form - Coming soon!');
    },
    handleViewSupplier(supplier) {
      alert(`View details for ${supplier.name} - Coming soon!`);
    },
    handleEditSupplier(supplier) {
      alert(`Edit ${supplier.name} - Coming soon!`);
    },
    handleContactSupplier(supplier) {
      alert(`Contact ${supplier.name} at ${supplier.contact}`);
    }
  }
};
</script>

<style scoped>
.suppliers-page {
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

.suppliers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 1.5rem;
}

.supplier-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.supplier-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.supplier-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.supplier-title h3 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--primary-color);
}

.supplier-code {
  font-size: 0.75rem;
  color: var(--secondary-color);
  font-family: monospace;
}

.supplier-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-preferred {
  background: #e3f2fd;
  color: #1976d2;
}

.badge-esg {
  background: #e8f5e9;
  color: #388e3c;
}

.badge-approved {
  background: #f3e5f5;
  color: #7b1fa2;
}

.supplier-details {
  margin-bottom: 1rem;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color);
}

.detail-row svg {
  color: var(--accent-color);
  flex-shrink: 0;
}

.supplier-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin: 1rem 0;
  padding: 1rem;
  background: var(--hover-color);
  border-radius: 8px;
}

.metric {
  text-align: center;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--secondary-color);
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--primary-color);
}

.supplier-info {
  margin-bottom: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.info-item {
  font-size: 0.875rem;
  color: var(--text-color);
  margin-bottom: 0.5rem;
}

.info-item strong {
  color: var(--secondary-color);
  font-weight: 600;
}

.supplier-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-action {
  flex: 1;
  padding: 0.625rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-view {
  background: var(--accent-color);
  color: white;
}

.btn-view:hover {
  background: #0056b3;
}

.btn-edit {
  background: white;
  color: var(--accent-color);
  border: 2px solid var(--accent-color);
}

.btn-edit:hover {
  background: var(--accent-color);
  color: white;
}

.btn-contact {
  background: white;
  color: var(--secondary-color);
  border: 2px solid var(--border-color);
}

.btn-contact:hover {
  background: var(--hover-color);
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 1rem;
  }

  .suppliers-grid {
    grid-template-columns: 1fr;
  }

  .supplier-metrics {
    grid-template-columns: 1fr;
  }

  .supplier-actions {
    flex-direction: column;
  }
}
</style>
