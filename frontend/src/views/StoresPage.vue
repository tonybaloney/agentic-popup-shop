<template>
  <div class="stores-page">
    <div class="container">
      <h1 class="page-title">Our Popup Shop Locations</h1>
      <p class="page-subtitle">Visit us at any of our {{ stores.length }} locations</p>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading stores...</p>
      </div>

      <div class="stores-grid" v-if="!loading">
        <div v-for="store in stores" :key="store.id" class="store-card">
          <!-- Use picture element for stores with valid images -->
          <picture v-if="!failedImages.has(store.id)">
            <source :srcset="getStoreImageWebP(store)" type="image/webp">
            <img 
              :src="getStoreImage(store)" 
              :alt="store.name"
              class="store-image"
              @error="handleImageError($event, store)"
            />
          </picture>
          <!-- Fallback for stores with missing images -->
          <img 
            v-else
            src="/images/store.png"
            :alt="store.name"
            class="store-image"
          />
          <div class="store-header">
            <h3 class="store-name">{{ store.name }}</h3>
            <span class="store-badge" :class="store.status">{{ store.status }}</span>
          </div>
          <div class="store-details">
            <div class="detail-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                <circle cx="12" cy="10" r="3"/>
              </svg>
              <span>{{ store.location }}</span>
            </div>
            <div class="detail-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
              <span>{{ store.hours }}</span>
            </div>
            <div class="detail-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
              <span>{{ store.products }} products in stock</span>
            </div>
          </div>
          <button class="btn btn-outline store-btn" @click="handleDirections(store)">
            Get Directions
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { apiClient, config } from '../config/api';

export default {
  name: 'StoresPage',
  data() {
    return {
      stores: [],
      loading: true,
      error: null,
      failedImages: new Set(), // Track stores with failed images
      // Static fallback data
      staticStores: [
        {
          id: 1,
          name: 'Zava Pop-Up Pike Place',
          location: 'Pike Place Market, Seattle, WA',
          location_key: 'pike_place',
          hours: 'Mon-Sun: 9am-8pm',
          products: 52,
          status: 'Open',
          is_online: false
        },
        {
          id: 2,
          name: 'Zava Pop-Up Bellevue Square',
          location: 'Bellevue Square Mall, Bellevue, WA',
          location_key: 'bellevue_square',
          hours: 'Mon-Sat: 10am-9pm, Sun: 11am-7pm',
          products: 47,
          status: 'Open',
          is_online: false
        },
        {
          id: 3,
          name: 'Zava Pop-Up Kirkland Waterfront',
          location: 'Kirkland Waterfront, Kirkland, WA',
          location_key: 'kirkland_waterfront',
          hours: 'Mon-Sun: 10am-7pm',
          products: 54,
          status: 'Open',
          is_online: false
        },
        {
          id: 4,
          name: 'Zava Pop-Up Tacoma Mall',
          location: 'Tacoma Mall, Tacoma, WA',
          location_key: 'tacoma_mall',
          hours: 'Mon-Sat: 10am-9pm, Sun: 11am-6pm',
          products: 50,
          status: 'Open',
          is_online: false
        },
        {
          id: 5,
          name: 'Zava Pop-Up Spokane Pavilion',
          location: 'Spokane Pavilion, Spokane, WA',
          location_key: 'spokane_pavilion',
          hours: 'Mon-Sun: 10am-8pm',
          products: 52,
          status: 'Open',
          is_online: false
        },
        {
          id: 6,
          name: 'Zava Pop-Up Everett Station',
          location: 'Everett Station Square, Everett, WA',
          location_key: 'everett_station',
          hours: 'Mon-Sat: 10am-8pm, Sun: 11am-6pm',
          products: 47,
          status: 'Open',
          is_online: false
        },
        {
          id: 7,
          name: 'Zava Pop-Up Redmond Town Center',
          location: 'Redmond Town Center, Redmond, WA',
          location_key: 'redmond_town_center',
          hours: 'Mon-Sun: 10am-7pm',
          products: 45,
          status: 'Open',
          is_online: false
        },
        {
          id: 8,
          name: 'Zava Online Store',
          location: 'Online Warehouse, Seattle, WA',
          location_key: 'online',
          hours: '24/7 Online',
          products: 120,
          status: 'Online',
          is_online: true
        }
      ]
    };
  },
  mounted() {
    this.fetchStores();
  },
  methods: {
    async fetchStores() {
      try {
        const response = await apiClient.get('/api/stores');
        this.stores = response.data.stores;
        this.loading = false;
        console.log('✅ Loaded stores from API:', this.stores.length);
      } catch (err) {
        console.error('❌ Error fetching stores:', err);
        this.error = 'Unable to load live store data from server';
        this.stores = this.staticStores;
        this.loading = false;
      }
    },
    getStoreImage(store) {
      // Use location_key if available, otherwise generate from name
      const key = store.location_key || store.name.toLowerCase().replace(/\s+/g, '_');
      return `/images/store_${key}.png`;
    },
    getStoreImageWebP(store) {
      // Use location_key if available, otherwise generate from name
      const key = store.location_key || store.name.toLowerCase().replace(/\s+/g, '_');
      return `/images/store_${key}.webp`;
    },
    handleImageError(event, store) {
      // Mark this store as having a failed image
      this.failedImages.add(store.id);
      // Force re-render by creating a new Set
      this.failedImages = new Set(this.failedImages);
      console.log(`⚠️ Image not found for store: ${store.name}, using fallback`);
    },
    handleDirections(store) {
      // Open Google Maps with store location
      const query = encodeURIComponent(store.location);
      window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, '_blank');
    }
  }
};
</script>

<style scoped>
.stores-page {
  min-height: 100vh;
  padding: 3rem 0;
}

.page-title {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 1rem;
  color: var(--primary-color);
}

.page-subtitle {
  text-align: center;
  font-size: 1.125rem;
  color: var(--secondary-color);
  margin-bottom: 3rem;
}

/* Loading State */
.loading-state {
  text-align: center;
  padding: 4rem 0;
}

.spinner {
  width: 3rem;
  height: 3rem;
  border: 4px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  color: var(--secondary-color);
  font-size: 1.1rem;
}

/* Error State */
.error-state {
  text-align: center;
  padding: 2rem;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.error-state p {
  margin: 0.5rem 0;
  color: #856404;
  font-size: 1rem;
}

.error-sub {
  font-size: 0.9rem;
  opacity: 0.8;
}

.stores-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 2rem;
}

.store-card {
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s;
}

.store-card:hover {
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
}

.store-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
  background: var(--hover-color);
}

.store-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  padding: 1.5rem 2rem 0 2rem;
}

.store-name {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--primary-color);
  flex: 1;
}

.store-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.store-badge.Open {
  background: #d4edda;
  color: #155724;
}

.store-badge.Online {
  background: #cce5ff;
  color: #004085;
}

.store-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 0 2rem;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--text-color);
  font-size: 0.9rem;
}

.detail-item svg {
  flex-shrink: 0;
  color: var(--accent-color);
}

.store-btn {
  width: calc(100% - 4rem);
  margin: 0 2rem 2rem 2rem;
}

/* Responsive */
@media (max-width: 768px) {
  .page-title {
    font-size: 2rem;
  }

  .stores-grid {
    grid-template-columns: 1fr;
  }
}
</style>
