<template>
  <div class="ai-agent-page">
    <!-- Header -->
    <div class="page-header">
      <router-link to="/management/inventory" class="back-link">
        <i class="bi bi-arrow-left"></i> Back to Inventory
      </router-link>
      <h1><i class="bi bi-robot"></i> AI Restocking Agent</h1>
      <p class="subtitle">Analyze inventory levels and get intelligent restocking recommendations</p>
    </div>

    <!-- Main Content -->
    <div class="agent-container">
      <!-- Hero Section -->
      <div class="hero-section" v-if="!isRunning && !hasCompleted">
        <div class="hero-content">
          <i class="bi bi-lightbulb hero-icon"></i>
          <h2>Intelligent Inventory Analysis</h2>
          <p>
            Our AI agent analyzes your inventory across all stores, identifies low-stock items,
            and provides prioritized restocking recommendations based on company policies and budget constraints.
          </p>
          <div class="features">
            <div class="feature">
              <i class="bi bi-check-circle-fill"></i>
              <span>Real-time inventory analysis</span>
            </div>
            <div class="feature">
              <i class="bi bi-check-circle-fill"></i>
              <span>Policy-aware recommendations</span>
            </div>
            <div class="feature">
              <i class="bi bi-check-circle-fill"></i>
              <span>Budget optimization</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Section -->
      <div class="input-section" v-if="!isRunning && !hasCompleted">
        <div class="mock-mode-badge" v-if="useMockData">
          <i class="bi bi-info-circle"></i>
          Running in demo mode (backend unavailable)
        </div>
        
        <div class="input-group" v-if="isAdmin">
          <label for="store-select" class="input-label">
            <i class="bi bi-shop"></i> Select Store
          </label>
          <select 
            id="store-select" 
            v-model="selectedStoreId" 
            class="store-select"
            :disabled="loadingStores"
          >
            <option v-if="loadingStores" :value="null">Loading stores...</option>
            <option v-for="store in stores" :key="store.id" :value="store.id">
              {{ store.name }} {{ store.is_online ? '(Online)' : '' }}
            </option>
          </select>
        </div>

        <!-- Store Info for Store Managers (Read-only) -->
        <div class="input-group store-info-readonly" v-else>
          <label class="input-label">
            <i class="bi bi-shop"></i> Store
          </label>
          <div class="store-display">
            {{ stores[0]?.name || 'Loading...' }}
          </div>
        </div>
        
        <div class="input-group">
          <label for="instructions" class="input-label">
            <i class="bi bi-chat-left-text"></i> Instructions for AI Agent
          </label>
          <textarea
            id="instructions"
            v-model="userInstructions"
            class="instructions-input"
            rows="4"
            placeholder="Enter your instructions for the AI agent..."
          ></textarea>
        </div>
        
        <button 
          @click="startAnalysis" 
          class="launch-button" 
          :disabled="!userInstructions.trim() || !selectedStoreId || loadingStores"
        >
          <i class="bi bi-rocket-takeoff"></i> Launch AI Analysis
        </button>
      </div>

      <!-- Progress Section with Steps -->
      <div class="progress-section" v-if="isRunning || events.length > 0">
        <div class="progress-card">
          <!-- Progress Header -->
          <div class="progress-header">
            <div class="header-left">
              <div class="spinner" v-if="isRunning"></div>
              <i class="bi bi-x-circle-fill error-icon" v-else-if="error"></i>
              <i class="bi bi-check-circle-fill complete-icon" v-else></i>
              <div>
                <h3>{{ error ? 'Analysis Failed' : (isRunning ? 'AI Analysis in Progress' : 'Analysis Complete') }}</h3>
                <p class="progress-subtitle">{{ progressSummary }}</p>
              </div>
            </div>
            <button 
              v-if="events.length > 0" 
              @click="showDetails = !showDetails" 
              class="details-toggle"
            >
              <i :class="showDetails ? 'bi bi-chevron-up' : 'bi bi-chevron-down'"></i>
              {{ showDetails ? 'Hide Details' : 'Show Details' }}
            </button>
          </div>

          <!-- Progress Steps (always visible) -->
          <div class="progress-steps">
            <div 
              v-for="step in progressSteps" 
              :key="step.id"
              class="progress-step"
              :class="{ 
                'active': step.status === 'active', 
                'complete': step.status === 'complete',
                'pending': step.status === 'pending',
                'error': step.status === 'error'
              }"
            >
              <div class="step-indicator">
                <div class="spinner-small" v-if="step.status === 'active'"></div>
                <i class="bi bi-check-circle-fill" v-else-if="step.status === 'complete'"></i>
                <i class="bi bi-x-circle-fill" v-else-if="step.status === 'error'"></i>
                <i class="bi bi-circle" v-else></i>
              </div>
              <div class="step-content">
                <div class="step-title">{{ step.title }}</div>
                <div class="step-description" v-if="step.description">{{ step.description }}</div>
                <div class="step-time" v-if="step.timestamp">{{ formatStepDuration(step) }}</div>
              </div>
            </div>
          </div>

          <!-- Detailed Events (collapsible) -->
          <transition name="slide">
            <div class="events-details" v-if="showDetails && events.length > 0">
              <div class="details-header">
                <i class="bi bi-list-ul"></i>
                <span>Detailed Activity Log</span>
              </div>
              <div class="events-container">
                <div 
                  v-for="(event, index) in events" 
                  :key="index" 
                  class="event-item"
                  :class="{ 'fade-in': index === events.length - 1 }"
                >
                  <div class="event-bullet"></div>
                  <div class="event-details">
                    <div class="event-content">{{ event.message }}</div>
                    <div class="event-time">{{ formatTime(event.timestamp) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>

      <!-- Final Output - Restocking Recommendations -->
      <div class="output-section" v-if="restockingItems.length > 0 && !error">
        <div class="output-header">
          <i class="bi bi-check-circle-fill success-icon"></i>
          <h3>Restocking Recommendations</h3>
          <p class="output-subtitle">{{ restockingItems.length }} items need restocking. Select items to order.</p>
        </div>
        
        <!-- AI Summary -->
        <div class="summary-container" v-if="workflowSummary">
          <div class="summary-header">
            <i class="bi bi-chat-left-text"></i>
            <span>AI Analysis Summary</span>
          </div>
          <div class="summary-content markdown-content" v-html="renderedSummary"></div>
        </div>
        
        <div class="restocking-table-container">
          <table class="restocking-table">
            <thead>
              <tr>
                <th class="checkbox-col">
                  <input 
                    type="checkbox" 
                    :checked="selectedItems.length === restockingItems.length"
                    @change="toggleSelectAll"
                    class="table-checkbox"
                  />
                </th>
                <th class="image-col">Image</th>
                <th>SKU</th>
                <th>Product Name</th>
                <th>Category</th>
                <th class="number-col">Current Stock</th>
                <th class="number-col">Unit Cost</th>
                <th class="number-col">Order Qty</th>
                <th class="number-col">Total Cost</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="(item, index) in restockingItems" 
                :key="item.sku"
                :class="{ 'selected-row': item.selected }"
              >
                <td class="checkbox-col">
                  <input 
                    type="checkbox" 
                    v-model="item.selected"
                    class="table-checkbox"
                  />
                </td>
                <td class="image-col">
                  <img 
                    :src="item.image_url ? `/images/${item.image_url}` : `/images/${item.sku}.png`" 
                    :alt="item.product_name" 
                    class="product-image"
                    @error="handleImageError"
                  />
                </td>
                <td class="sku-col">{{ item.sku }}</td>
                <td class="product-col">
                  <a 
                    :href="`/management/products/${item.sku}`" 
                    class="product-link"
                  >
                    {{ item.product_name }}
                  </a>
                </td>
                <td>{{ item.category_name }}</td>
                <td class="number-col">
                  <span class="stock-badge" :class="{ 'low-stock': item.stock_level < 10 }">
                    {{ item.stock_level }}
                  </span>
                </td>
                <td class="number-col">${{ item.cost.toFixed(2) }}</td>
                <td class="number-col">
                  <input 
                    type="number" 
                    v-model.number="item.quantity" 
                    min="1" 
                    max="1000"
                    class="quantity-input"
                  />
                </td>
                <td class="number-col total-col">
                  ${{ (item.cost * item.quantity).toFixed(2) }}
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="totals-row">
                <td colspan="8" class="total-label">
                  <strong>Total Order Cost ({{ selectedCount }} items):</strong>
                </td>
                <td class="number-col total-col">
                  <strong>${{ totalOrderCost.toFixed(2) }}</strong>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
        
        <div class="output-actions">
          <button 
            @click="placeOrder" 
            class="order-button"
            :disabled="selectedCount === 0 || isOrdering"
          >
            <i class="bi bi-cart-check"></i>
            {{ isOrdering ? 'Placing Order...' : `Place Order (${selectedCount} items)` }}
          </button>
          <button @click="resetAnalysis" class="reset-button secondary">
            <i class="bi bi-arrow-counterclockwise"></i> Run Another Analysis
          </button>
        </div>
      </div>

      <!-- Error Display -->
      <div class="error-section" v-if="error && !isRunning">
        <div class="error-header">
          <i class="bi bi-exclamation-triangle-fill"></i>
          <h3>Error Occurred</h3>
        </div>
        <div class="error-content">{{ error }}</div>
        <button @click="resetAnalysis" class="retry-button">
          <i class="bi bi-arrow-clockwise"></i> Try Again
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import { apiClient, config } from '../../config/api'
import { authStore } from '../../stores/auth'

// Configure marked options
marked.setOptions({
  breaks: true,
  gfm: true
})

// State
const userInstructions = ref('Analyze inventory and recommend restocking priorities')
const selectedStoreId = ref(null)
const stores = ref([])
const loadingStores = ref(false)
const isRunning = ref(false)
const hasCompleted = ref(false)
const events = ref([])
const finalOutput = ref(null)
const restockingItems = ref([])
const selectedItems = ref([])
const workflowSummary = ref('')
const error = ref(null)
const showDetails = ref(false)
const currentStep = ref(0)
const currentTime = ref(new Date())
const isOrdering = ref(false)
const useMockData = ref(false)
let ws = null
let timeUpdateInterval = null
let mockTimeouts = []

// Progress steps - now dynamically populated from backend events
const progressSteps = ref([])

// Progress summary
const progressSummary = computed(() => {
  if (error.value) {
    return 'Analysis failed - please review the error below'
  }
  if (!isRunning.value && hasCompleted.value) {
    return `Analysis completed successfully with ${events.value.length} events processed`
  }
  const activeStep = progressSteps.value.find(s => s.status === 'active')
  return activeStep ? activeStep.title : 'Connecting to AI Agent...'
})

// Computed properties for restocking items
const selectedCount = computed(() => {
  return restockingItems.value.filter(item => item.selected).length
})

const totalOrderCost = computed(() => {
  return restockingItems.value
    .filter(item => item.selected)
    .reduce((total, item) => total + (item.cost * item.quantity), 0)
})

// Render markdown output
const renderedMarkdown = computed(() => {
  if (!finalOutput.value) return ''
  try {
    return marked.parse(finalOutput.value)
  } catch (err) {
    console.error('Error rendering markdown:', err)
    return `<pre>${finalOutput.value}</pre>`
  }
})

// Render workflow summary markdown
const renderedSummary = computed(() => {
  if (!workflowSummary.value) return ''
  try {
    return marked.parse(workflowSummary.value)
  } catch (err) {
    console.error('Error rendering summary markdown:', err)
    return `<pre>${workflowSummary.value}</pre>`
  }
})

// Check if user is admin
const isAdmin = computed(() => authStore.user?.role === 'admin')

// Fetch stores from API
const fetchStores = async () => {
  loadingStores.value = true
  try {
    // If user is a store manager, use their store_id directly
    if (!isAdmin.value && authStore.user?.store_id) {
      selectedStoreId.value = authStore.user.store_id
      stores.value = [{
        id: authStore.user.store_id,
        name: authStore.user.store_name || 'Your Store',
        is_online: false
      }]
      loadingStores.value = false
      return
    }

    // For admin users, fetch all stores
    const response = await apiClient.get('/api/stores')
    stores.value = response.data.stores || []
    // Set first store as default if available
    if (stores.value.length > 0 && !selectedStoreId.value) {
      selectedStoreId.value = stores.value[0].id
    }
  } catch (err) {
    console.error('Failed to fetch stores:', err)
    console.log('🎭 Using mock store for demo mode')
    // Provide a fallback mock store so the workflow can still be tested
    stores.value = [
      {
        id: authStore.user?.store_id || 1,
        name: authStore.user?.store_name || 'Popup Downtown Redmond',
        is_online: false
      }
    ]
    selectedStoreId.value = authStore.user?.store_id || 1
  } finally {
    loadingStores.value = false
  }
}

// Mock WebSocket data - replays recorded messages with realistic timing
const runMockWorkflow = () => {
  console.log('🎭 Running mock workflow (backend unavailable)')
  
  addEvent('Connected to AI Agent (Mock Mode)')
  
  // Clear any existing timeouts
  mockTimeouts.forEach(timeout => clearTimeout(timeout))
  mockTimeouts = []
  
  const now = new Date()
  
  // Mock messages with realistic delays
  const mockMessages = [
    { delay: 100, data: {"type":"started","message":"AI Agent workflow initiated...","timestamp":now.toISOString()} },
    { delay: 200, data: {"type":"workflow_started","event":"None","timestamp":now.toISOString()} },
    { delay: 2000, data: {"type":"step_started","event":null,"id":"Stock Analyzer","timestamp":new Date(now.getTime() + 2000).toISOString()} },
    { delay: 5000, data: {"type":"step_completed","event":null,"id":"Stock Analyzer","timestamp":new Date(now.getTime() + 5000).toISOString()} },
    { delay: 5100, data: {"type":"step_started","event":null,"id":"Summarizer","timestamp":new Date(now.getTime() + 5100).toISOString()} },
    { delay: 8000, data: {"type":"workflow_output","event":{"summary":"## Inventory Analysis Complete\n\nBased on my analysis of the **Popup Downtown Redmond** store inventory, I've identified **9 products** that require immediate restocking attention:\n\n### Critical Low Stock Items\n- **Thermal Winter Socks** and **Mesh Athletic Sneakers** both have only **2 units** remaining\n- **Cozy Slipper Socks** has **4 units** in stock\n\n### Priority Recommendations\n1. **Accessories**: 2 items need restocking (winter socks and slipper socks)\n2. **Footwear**: 1 critical item (athletic sneakers)\n3. **Apparel**: 3 items requiring attention (tees, shorts, jeans)\n4. **Outerwear**: 3 items at moderate stock levels (9 units each)\n\n**Total estimated restock cost**: Consider budgeting approximately **$500-600** for the recommended quantities.","items":[{"sku":"ACC-SK-005","product_name":"Thermal Winter Socks","category_name":"Accessories","stock_level":2,"cost":14.99},{"sku":"ACC-SK-008","product_name":"Cozy Slipper Socks","category_name":"Accessories","stock_level":4,"cost":15.99},{"sku":"FW-SN-006","product_name":"Mesh Athletic Sneakers","category_name":"Footwear","stock_level":2,"cost":54.99},{"sku":"APP-TS-002","product_name":"V-Neck Casual Tee","category_name":"Apparel - Tops","stock_level":3,"cost":17.99},{"sku":"APP-SH-003","product_name":"Cargo Shorts","category_name":"Apparel - Bottoms","stock_level":3,"cost":34.99},{"sku":"APP-JN-001","product_name":"Classic Straight Leg Jeans","category_name":"Apparel - Bottoms","stock_level":4,"cost":49.99},{"sku":"OUT-CT-004","product_name":"Rain Coat Long","category_name":"Outerwear","stock_level":9,"cost":89.99},{"sku":"OUT-JK-005","product_name":"Puffer Jacket","category_name":"Outerwear","stock_level":9,"cost":89.99},{"sku":"OUT-JK-010","product_name":"Quilted Vest","category_name":"Outerwear","stock_level":9,"cost":49.99}]},"timestamp":new Date(now.getTime() + 8000).toISOString()} },
    { delay: 8100, data: {"type":"step_completed","event":null,"id":"Summarizer","timestamp":new Date(now.getTime() + 8100).toISOString()} },
    { delay: 8200, data: {"type":"completed","message":"Workflow completed successfully","output":{"summary":"## Inventory Analysis Complete\n\nBased on my analysis of the **Popup Downtown Redmond** store inventory, I've identified **9 products** that require immediate restocking attention:\n\n### Critical Low Stock Items\n- **Thermal Winter Socks** and **Mesh Athletic Sneakers** both have only **2 units** remaining\n- **Cozy Slipper Socks** has **4 units** in stock\n\n### Priority Recommendations\n1. **Accessories**: 2 items need restocking (winter socks and slipper socks)\n2. **Footwear**: 1 critical item (athletic sneakers)\n3. **Apparel**: 3 items requiring attention (tees, shorts, jeans)\n4. **Outerwear**: 3 items at moderate stock levels (9 units each)\n\n**Total estimated restock cost**: Consider budgeting approximately **$500-600** for the recommended quantities.","items":[{"sku":"ACC-SK-005","product_name":"Thermal Winter Socks","category_name":"Accessories","stock_level":2,"cost":14.99},{"sku":"ACC-SK-008","product_name":"Cozy Slipper Socks","category_name":"Accessories","stock_level":4,"cost":15.99},{"sku":"FW-SN-006","product_name":"Mesh Athletic Sneakers","category_name":"Footwear","stock_level":2,"cost":54.99},{"sku":"APP-TS-002","product_name":"V-Neck Casual Tee","category_name":"Apparel - Tops","stock_level":3,"cost":17.99},{"sku":"APP-SH-003","product_name":"Cargo Shorts","category_name":"Apparel - Bottoms","stock_level":3,"cost":34.99},{"sku":"APP-JN-001","product_name":"Classic Straight Leg Jeans","category_name":"Apparel - Bottoms","stock_level":4,"cost":49.99},{"sku":"OUT-CT-004","product_name":"Rain Coat Long","category_name":"Outerwear","stock_level":9,"cost":89.99},{"sku":"OUT-JK-005","product_name":"Puffer Jacket","category_name":"Outerwear","stock_level":9,"cost":89.99},{"sku":"OUT-JK-010","product_name":"Quilted Vest","category_name":"Outerwear","stock_level":9,"cost":49.99}]},"timestamp":new Date(now.getTime() + 8200).toISOString()} }
  ]
  
  // Schedule all mock messages
  mockMessages.forEach(msg => {
    const timeout = setTimeout(async () => {
      await handleWebSocketMessage({ data: JSON.stringify(msg.data) })
    }, msg.delay)
    mockTimeouts.push(timeout)
  })
}

// Handle WebSocket message (extracted for reuse with mock)
const handleWebSocketMessage = async (event) => {
  try {
    const data = JSON.parse(event.data)
    
    console.log('📥 WebSocket message received:', data)
    
    if (data.type === 'started') {
      addEvent('AI Agent workflow started')
    } else if (data.type === 'workflow_started') {
      addEvent(`Workflow: ${data.event}`)
    } else if (data.type === 'step_started') {
      // Add new step dynamically when it starts
      console.log('🟢 Step started:', data.id, data.event, data.timestamp)
      addProgressStep(data.id, 'active', data.event, data.timestamp)
      addEvent(`Started: ${data.id} - ${data.event}`)
    } else if (data.type === 'step_completed') {
      // Mark step as complete
      console.log('✅ Step completed:', data.id, data.event, data.timestamp)
      updateProgressStep(data.id, 'complete', data.event, data.timestamp)
      addEvent(`Completed: ${data.id}`)
    } else if (data.type === 'step_failed') {
      // Mark step as failed and stop the workflow
      console.log('❌ Step failed:', data.id, data.event, data.timestamp)
      const errorMsg = data.event || 'Step failed'
      updateProgressStep(data.id, 'error', errorMsg, data.timestamp)
      addEvent(`❌ Failed: ${data.id} - ${errorMsg}`)
      
      // Set error state to display error section
      error.value = `Step "${data.id}" failed: ${errorMsg}`
      isRunning.value = false
      hasCompleted.value = false
      
      console.log('🛑 Stopping workflow due to step failure')
      
      // Close WebSocket immediately
      if (ws && !useMockData.value) {
        try {
          ws.close()
        } catch (e) {
          console.error('Error closing WebSocket:', e)
        }
        ws = null
      }
    } else if (data.type === 'workflow_output') {
      addEvent('Workflow output generated')
      console.log('📦 Workflow output:', data.event)
      
      // Extract summary if present
      if (data.event && data.event.summary) {
        workflowSummary.value = data.event.summary
        console.log('📝 Workflow summary loaded')
      }
      
      // Parse the workflow output - it contains items array
      if (data.event && data.event.items && Array.isArray(data.event.items)) {
        // Enrich items with full product details (including image_url)
        const enrichedItems = await enrichItemsWithProductDetails(data.event.items)
        
        restockingItems.value = enrichedItems.map(item => ({
          ...item,
          selected: true, // Select all by default
          quantity: 10 // Default reorder quantity
        }))
        selectedItems.value = restockingItems.value.map((_, index) => index)
        console.log('✅ Loaded restocking items:', restockingItems.value.length)
      }
      
      finalOutput.value = data.event
    } else if (data.type === 'event') {
      // Display the event
      addEvent(data.event)
    } else if (data.type === 'completed') {
      addEvent('Analysis completed successfully')
      if (data.output) {
        finalOutput.value = data.output
      }
      // Complete all active steps
      progressSteps.value.forEach(step => {
        if (step.status === 'active') {
          step.status = 'complete'
        }
      })
      isRunning.value = false
      hasCompleted.value = true
      if (ws && !useMockData.value) {
        ws.close()
        ws = null
      }
    } else if (data.type === 'error') {
      // Handle general error - support both 'error' and 'message' fields
      const errorMessage = data.error || data.message || 'An unknown error occurred'
      addEvent(`❌ Error: ${errorMessage}`)
      
      // Set error state
      error.value = errorMessage
      isRunning.value = false
      hasCompleted.value = false
      
      console.log('🛑 Stopping workflow due to error')
      
      // Mark current active step as failed
      const activeStep = progressSteps.value.find(s => s.status === 'active')
      if (activeStep) {
        activeStep.status = 'error'
        activeStep.description = 'Failed'
      }
      
      // Close WebSocket immediately
      if (ws && !useMockData.value) {
        try {
          ws.close()
        } catch (e) {
          console.error('Error closing WebSocket:', e)
        }
        ws = null
      }
    }
  } catch (err) {
    console.error('Failed to parse WebSocket message:', err)
    const errorMsg = 'Failed to process server response'
    addEvent(errorMsg)
    error.value = errorMsg
    isRunning.value = false
  }
}

// Start analysis
const startAnalysis = () => {
  // Reset state
  events.value = []
  finalOutput.value = null
  error.value = null
  isRunning.value = true
  hasCompleted.value = false
  showDetails.value = false
  currentStep.value = 0
  restockingItems.value = []
  selectedItems.value = []
  
  // Clear any mock timeouts
  mockTimeouts.forEach(timeout => clearTimeout(timeout))
  mockTimeouts = []
  
  // Reset progress steps
  progressSteps.value = []

  // Try to connect to WebSocket with timeout
  const wsUrl = '/ws/management/ai-agent/inventory'
  ws = new WebSocket(wsUrl)
  
  let connectionEstablished = false

  // Set a timeout to detect connection failure (3 seconds)
  const connectionTimeout = setTimeout(() => {
    if (!connectionEstablished && !useMockData.value) {
      console.warn('⏱️ WebSocket connection timeout - switching to mock mode')
      useMockData.value = true
      
      // Close the hanging connection attempt
      if (ws) {
        try {
          ws.close()
        } catch (e) {
          // Ignore errors on close
        }
        ws = null
      }
      
      // Run mock workflow
      runMockWorkflow()
    }
  }, config.timeout)
  
  mockTimeouts.push(connectionTimeout)

  ws.onopen = () => {
    connectionEstablished = true
    useMockData.value = false
    clearTimeout(connectionTimeout)
    
    addEvent('Connected to AI Agent')
    
    // Get authentication token
    const token = authStore.getToken()
    if (!token) {
      error.value = 'Authentication required. Please log in again.'
      isRunning.value = false
      ws?.close()
      return
    }
    
    // Send the user instructions with authentication token
    // Store managers' store_id will be automatically used by the backend
    ws.send(JSON.stringify({
      token: token,
      message: userInstructions.value,
      store_id: selectedStoreId.value  // Only used by admin, ignored for store managers
    }))
  }

  ws.onmessage = async (event) => {
    await handleWebSocketMessage(event)
  }

  ws.onerror = (err) => {
    console.error('WebSocket error:', err)
    
    // Only switch to mock if not already established
    if (!connectionEstablished && !useMockData.value) {
      console.log('🎭 WebSocket error - switching to mock mode...')
      clearTimeout(connectionTimeout)
      useMockData.value = true
      ws = null
      
      // Run mock workflow
      runMockWorkflow()
    }
  }

  ws.onclose = (event) => {
    console.log('🔌 WebSocket closed:', event.code, event.reason)
    
    // If connection was never established and we're not in mock mode, switch to mock
    if (!connectionEstablished && !useMockData.value) {
      console.log('🎭 WebSocket closed before connection - switching to mock mode...')
      clearTimeout(connectionTimeout)
      useMockData.value = true
      ws = null
      runMockWorkflow()
    } 
    // Only update state if we're still running and no error has been set
    else if (isRunning.value && !error.value && !useMockData.value) {
      addEvent('Connection closed unexpectedly')
      isRunning.value = false
    }
    
    if (!useMockData.value) {
      ws = null
    }
  }
}

// Add a new progress step dynamically
const addProgressStep = (stepId, status, description = '', timestamp = '') => {
  console.log('➕ Adding progress step:', { stepId, status, description, timestamp })
  
  // Check if step already exists
  const existingStep = progressSteps.value.find(s => s.id === stepId)
  if (existingStep) {
    // Update existing step
    console.log('🔄 Updating existing step:', stepId)
    existingStep.status = status
    existingStep.description = description
    existingStep.startTime = timestamp ? new Date(timestamp) : null
    existingStep.timestamp = existingStep.startTime
  } else {
    // Add new step - store the actual Date object for reactive updates
    const startTime = timestamp ? new Date(timestamp) : null
    const newStep = {
      id: stepId,
      title: stepId, // Use the executor ID as the title
      description: description,
      status: status,
      startTime: startTime,
      endTime: null,
      timestamp: startTime
    }
    console.log('✨ Creating new step:', newStep)
    progressSteps.value.push(newStep)
    console.log('📊 Total steps now:', progressSteps.value.length)
  }
}

// Update an existing progress step
const updateProgressStep = (stepId, status, description = '', timestamp = '') => {
  console.log('🔄 Updating progress step:', { stepId, status, description, timestamp })
  const step = progressSteps.value.find(s => s.id === stepId)
  if (step) {
    console.log('✅ Found step to update:', step.id)
    step.status = status
    if (description) {
      step.description = description
    }
    // When completing or failing a step, set endTime
    if ((status === 'complete' || status === 'error') && timestamp) {
      step.endTime = new Date(timestamp)
    }
    if (timestamp) {
      step.timestamp = new Date(timestamp)
    }
  } else {
    console.warn('⚠️ Step not found for update:', stepId)
  }
}

// Format step duration based on status
// Shows "Running for XX" when active, "Took XX" when complete/failed
const formatStepDuration = (step) => {
  if (!step.startTime) return ''
  
  try {
    // Access currentTime.value to make this reactive
    const now = currentTime.value
    
    // If step is complete or failed, use endTime - startTime
    if ((step.status === 'complete' || step.status === 'error') && step.endTime) {
      const diffInSeconds = Math.floor((step.endTime - step.startTime) / 1000)
      return `Took ${formatDuration(diffInSeconds)}`
    }
    
    // If step is active, use currentTime - startTime
    if (step.status === 'active') {
      const diffInSeconds = Math.floor((now - step.startTime) / 1000)
      return `Running for ${formatDuration(diffInSeconds)}`
    }
    
    return ''
  } catch (err) {
    return ''
  }
}

// Helper to format duration into human readable string
const formatDuration = (seconds) => {
  if (seconds < 1) {
    return 'less than a second'
  } else if (seconds < 60) {
    return seconds === 1 ? '1 second' : `${seconds} seconds`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    if (remainingSeconds === 0) {
      return minutes === 1 ? '1 minute' : `${minutes} minutes`
    }
    return `${minutes}m ${remainingSeconds}s`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (minutes === 0) {
      return hours === 1 ? '1 hour' : `${hours} hours`
    }
    return `${hours}h ${minutes}m`
  }
}

// Format timestamp to relative time (e.g., "20 seconds ago")
// Uses currentTime.value to trigger reactive updates
const formatRelativeTime = (date) => {
  if (!date) return ''
  try {
    // Access currentTime.value to make this reactive
    const now = currentTime.value
    const diffInSeconds = Math.floor((now - date) / 1000)
    
    if (diffInSeconds < 5) {
      return 'just now'
    } else if (diffInSeconds < 60) {
      return `${diffInSeconds} seconds ago`
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60)
      return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600)
      return hours === 1 ? '1 hour ago' : `${hours} hours ago`
    } else {
      const days = Math.floor(diffInSeconds / 86400)
      return days === 1 ? '1 day ago' : `${days} days ago`
    }
  } catch (err) {
    return ''
  }
}

// Add event to the list
const addEvent = (message) => {
  events.value.push({
    message,
    timestamp: new Date()
  })
}

// Format timestamp
const formatTime = (date) => {
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}

// Toggle select all items
const toggleSelectAll = () => {
  const allSelected = selectedCount.value === restockingItems.value.length
  restockingItems.value.forEach(item => {
    item.selected = !allSelected
  })
}

// Enrich restocking items with full product details (including image_url)
const enrichItemsWithProductDetails = async (items) => {
  if (!items || items.length === 0) return []
  
  console.log('🔍 Enriching', items.length, 'items with product details...')
  
  try {
    // Fetch all products in parallel
    const productPromises = items.map(item => 
      apiClient.get(`/api/products/sku/${item.sku}`)
        .then(response => ({
          ...item,
          image_url: response.data.image_url,
          product_description: response.data.product_description,
          supplier_name: response.data.supplier_name,
          discontinued: response.data.discontinued
        }))
        .catch(err => {
          console.error(`Failed to fetch product details for SKU ${item.sku}:`, err)
          // Return original item if fetch fails
          return item
        })
    )
    
    const enrichedItems = await Promise.all(productPromises)
    console.log('✅ Enriched items with product details')
    return enrichedItems
    
  } catch (err) {
    console.error('Error enriching items:', err)
    // Return original items if enrichment fails
    return items
  }
}

// Handle image loading error
const handleImageError = (event) => {
  event.target.src = '/images/placeholder.png'
  event.target.onerror = null // Prevent infinite loop
}

// Place order for selected items
const placeOrder = async () => {
  const selectedProducts = restockingItems.value.filter(item => item.selected)
  
  if (selectedProducts.length === 0) {
    alert('Please select at least one item to order.')
    return
  }
  
  isOrdering.value = true
  
  try {
    // Prepare order data
    const orderData = {
      store_id: selectedStoreId.value,
      items: selectedProducts.map(item => ({
        sku: item.sku,
        product_name: item.product_name,
        quantity: item.quantity,
        unit_cost: item.cost,
        total_cost: item.cost * item.quantity
      })),
      total_cost: totalOrderCost.value
    }
    
    console.log('📦 Placing order:', orderData)
    
    // TODO: Replace with actual API endpoint when available
    // const response = await apiClient.post('/api/orders', orderData)
    
    // Simulate API call for now
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    alert(`Order placed successfully!\n\n${selectedProducts.length} items ordered\nTotal: $${totalOrderCost.value.toFixed(2)}`)
    
    // Reset the form
    resetAnalysis()
  } catch (err) {
    console.error('Failed to place order:', err)
    alert('Failed to place order. Please try again.')
  } finally {
    isOrdering.value = false
  }
}

// Reset analysis
const resetAnalysis = () => {
  events.value = []
  finalOutput.value = null
  restockingItems.value = []
  selectedItems.value = []
  workflowSummary.value = ''
  error.value = null
  isRunning.value = false
  hasCompleted.value = false
  showDetails.value = false
  currentStep.value = 0
  progressSteps.value = []
  isOrdering.value = false
  useMockData.value = false
  
  // Clear mock timeouts
  mockTimeouts.forEach(timeout => clearTimeout(timeout))
  mockTimeouts = []
  
  if (ws) {
    ws.close()
    ws = null
  }
}

// Lifecycle hooks
onMounted(() => {
  // Fetch stores on component mount
  fetchStores()
  
  // Update currentTime every second to trigger reactive time updates
  timeUpdateInterval = setInterval(() => {
    currentTime.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  // Clean up interval
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval)
  }
  // Clean up mock timeouts
  mockTimeouts.forEach(timeout => clearTimeout(timeout))
  mockTimeouts = []
  // Clean up WebSocket
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>

<style scoped>
.ai-agent-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: #6c757d;
  text-decoration: none;
  margin-bottom: 1rem;
  font-size: 0.95rem;
  transition: color 0.2s;
}

.back-link:hover {
  color: #495057;
}

.page-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #212529;
  margin-bottom: 0.5rem;
}

.page-header h1 i {
  color: #0d6efd;
  margin-right: 0.5rem;
}

.subtitle {
  color: #6c757d;
  font-size: 1.1rem;
}

.agent-container {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Hero Section */
.hero-section {
  text-align: center;
  padding: 2rem 0;
  border-bottom: 1px solid #e9ecef;
  margin-bottom: 2rem;
}

.hero-content {
  max-width: 700px;
  margin: 0 auto;
}

.hero-icon {
  font-size: 4rem;
  color: #ffc107;
  margin-bottom: 1rem;
}

.hero-section h2 {
  font-size: 1.75rem;
  font-weight: 600;
  color: #212529;
  margin-bottom: 1rem;
}

.hero-section p {
  color: #6c757d;
  font-size: 1.05rem;
  line-height: 1.6;
  margin-bottom: 2rem;
}

.features {
  display: flex;
  justify-content: center;
  gap: 2rem;
  flex-wrap: wrap;
}

.feature {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #28a745;
  font-weight: 500;
}

.feature i {
  font-size: 1.2rem;
}

/* Input Section */
.input-section {
  max-width: 800px;
  margin: 0 auto;
}

.mock-mode-badge {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #856404;
  font-weight: 500;
}

.mock-mode-badge i {
  font-size: 1.2rem;
  color: #ffc107;
}

.input-group {
  margin-bottom: 1.5rem;
}

.input-label {
  display: block;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.75rem;
  font-size: 1.05rem;
}

.input-label i {
  color: #0d6efd;
}

.store-select {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
  background-color: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.store-select:focus {
  outline: none;
  border-color: #0d6efd;
}

.store-select:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
}

.store-info-readonly .store-display {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 1rem;
  background-color: #f8f9fa;
  color: #495057;
  font-weight: 500;
}

.instructions-input {
  width: 100%;
  padding: 1rem;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  transition: border-color 0.2s;
}

.instructions-input:focus {
  outline: none;
  border-color: #0d6efd;
}

.launch-button {
  margin-top: 1.5rem;
  width: 100%;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.launch-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(13, 110, 253, 0.3);
}

.launch-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.launch-button i {
  font-size: 1.2rem;
}

/* Progress Section */
.progress-section {
  margin-top: 2rem;
}

.progress-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 1px solid #e9ecef;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 2px solid #e9ecef;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.progress-header h3 {
  color: #212529;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
}

.progress-subtitle {
  color: #6c757d;
  font-size: 0.95rem;
  margin: 0;
}

.spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 4px solid #e9ecef;
  border-top-color: #0d6efd;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

.spinner-small {
  width: 1.25rem;
  height: 1.25rem;
  border: 3px solid #e9ecef;
  border-top-color: #0d6efd;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.complete-icon {
  font-size: 2.5rem;
  color: #28a745;
  flex-shrink: 0;
}

.error-icon {
  font-size: 2.5rem;
  color: #dc3545;
  flex-shrink: 0;
}

.details-toggle {
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  color: #495057;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  white-space: nowrap;
}

.details-toggle:hover {
  background: #e9ecef;
  border-color: #ced4da;
}

/* Progress Steps */
.progress-steps {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.progress-step {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  position: relative;
}

.progress-step:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 0.75rem;
  top: 2rem;
  width: 2px;
  height: calc(100% + 1rem);
  background: #e9ecef;
}

.progress-step.complete:not(:last-child)::before {
  background: #28a745;
}

.progress-step.active:not(:last-child)::before {
  background: linear-gradient(to bottom, #28a745 50%, #e9ecef 50%);
}

.progress-step.error:not(:last-child)::before {
  background: linear-gradient(to bottom, #28a745 50%, #dc3545 50%);
}

.step-indicator {
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.step-indicator i {
  font-size: 1.5rem;
}

.progress-step.pending .step-indicator i {
  color: #dee2e6;
}

.progress-step.active .step-indicator i {
  color: #0d6efd;
}

.progress-step.complete .step-indicator i {
  color: #28a745;
}

.progress-step.error .step-indicator i {
  color: #dc3545;
}

.step-content {
  flex: 1;
  padding-top: 0.15rem;
}

.step-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: #212529;
  margin-bottom: 0.25rem;
}

.progress-step.pending .step-title {
  color: #adb5bd;
}

.progress-step.error .step-title {
  color: #dc3545;
}

.step-description {
  font-size: 0.9rem;
  color: #6c757d;
  font-style: italic;
}

.progress-step.error .step-description {
  color: #dc3545;
  font-weight: 500;
}

.step-time {
  font-size: 0.85rem;
  color: #878a8eff;
  margin-top: 0.25rem;
}

/* Events Details */
.events-details {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e9ecef;
}

.details-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 1rem;
  font-size: 1rem;
}

.details-header i {
  color: #0d6efd;
}

.events-container {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  max-height: 400px;
  overflow-y: auto;
}

.event-item {
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid #e9ecef;
}

.event-item:last-child {
  border-bottom: none;
}

.event-item.fade-in {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.event-bullet {
  width: 6px;
  height: 6px;
  background: #0d6efd;
  border-radius: 50%;
  margin-top: 0.5rem;
  flex-shrink: 0;
}

.event-details {
  flex: 1;
}

.event-content {
  color: #212529;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.event-time {
  font-size: 0.8rem;
  color: #868e96;
}

/* Slide transition */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
  max-height: 500px;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Output Section */
.output-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e9ecef;
}

.output-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.success-icon {
  font-size: 2rem;
  color: #28a745;
}

.output-header h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #28a745;
}

/* AI Summary */
.summary-container {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid #dee2e6;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 1rem;
  font-size: 1rem;
}

.summary-header i {
  color: #0d6efd;
  font-size: 1.2rem;
}

.summary-content {
  background: white;
  border-radius: 6px;
  padding: 1.25rem;
}

.output-content {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

/* Markdown Content Styling */
.markdown-content {
  color: #212529;
  line-height: 1.7;
}

.markdown-content > * {
  margin-left: 0 !important;
}

.markdown-content h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #212529;
  margin: 1.5rem 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #dee2e6;
}

.markdown-content h1:first-child {
  margin-top: 0;
}

.markdown-content h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #495057;
  margin: 1.5rem 0 0.75rem 0;
}

.markdown-content h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #495057;
  margin: 1.25rem 0 0.75rem 0;
}

.markdown-content p {
  margin: 0 0 1rem 0;
}

.markdown-content ul,
.markdown-content ol {
  margin: 0 0 1rem 0;
  padding-left: 2rem;
  list-style-position: outside;
}

.markdown-content ul {
  list-style-type: disc;
}

.markdown-content ol {
  list-style-type: decimal;
}

.markdown-content li {
  margin: 0.5rem 0;
  padding-left: 0.5rem;
}

.markdown-content ul ul,
.markdown-content ol ul {
  margin: 0.5rem 0;
  padding-left: 2rem;
  list-style-type: circle;
}

.markdown-content ul ul ul,
.markdown-content ol ol ul {
  list-style-type: square;
}

.markdown-content ol ol,
.markdown-content ul ol {
  margin: 0.5rem 0;
  padding-left: 2rem;
  list-style-type: lower-alpha;
}

.markdown-content ol ol ol,
.markdown-content ul ul ol {
  list-style-type: lower-roman;
}

.markdown-content strong {
  font-weight: 600;
  color: #212529;
}

.markdown-content em {
  font-style: italic;
  color: #495057;
}

.markdown-content code {
  background: #e9ecef;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: #d63384;
}

.markdown-content pre {
  background: #2d2d2d;
  color: #f8f9fa;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  margin: 1rem 0;
}

.markdown-content pre code {
  background: transparent;
  color: inherit;
  padding: 0;
  font-size: 0.9rem;
}

.markdown-content blockquote {
  border-left: 4px solid #0d6efd;
  padding: 1rem 0 1rem 1rem;
  margin: 1rem 0;
  color: #6c757d;
  font-style: italic;
}

.markdown-content blockquote p {
  margin: 0;
}

.markdown-content blockquote p:not(:last-child) {
  margin-bottom: 0.5rem;
}

.markdown-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  display: table;
}

.markdown-content th,
.markdown-content td {
  padding: 0.75rem;
  border: 1px solid #dee2e6;
  text-align: left;
}

.markdown-content th {
  background: #e9ecef;
  font-weight: 600;
}

.markdown-content tbody tr:nth-child(even) {
  background: #f8f9fa;
}

.markdown-content a {
  color: #0d6efd;
  text-decoration: none;
}

.markdown-content a:hover {
  text-decoration: underline;
}

.markdown-content hr {
  border: none;
  border-top: 1px solid #dee2e6;
  margin: 1.5rem 0;
}

/* Ensure nested lists have proper indentation */
.markdown-content li > ul,
.markdown-content li > ol {
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

/* Fix for any inline elements */
.markdown-content img {
  max-width: 100%;
  height: auto;
  margin: 1rem 0;
  display: block;
}

.reset-button {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  background: #28a745;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.reset-button:hover {
  background: #218838;
}

/* Error Section */
.error-section {
  margin-top: 2rem;
  padding: 2rem;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
}

.error-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.error-header i {
  font-size: 2rem;
  color: #dc3545;
}

.error-header h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #dc3545;
}

.error-content {
  color: #856404;
  font-size: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border-radius: 4px;
}

.retry-button {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  background: #dc3545;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.retry-button:hover {
  background: #c82333;
}

/* Restocking Table */
.output-subtitle {
  color: #6c757d;
  margin-top: 0.5rem;
  font-size: 1rem;
  font-weight: normal;
}

.restocking-table-container {
  margin: 1.5rem 0;
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.restocking-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.restocking-table thead {
  background: #f8f9fa;
  border-bottom: 2px solid #dee2e6;
}

.restocking-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #495057;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.restocking-table td {
  padding: 1rem;
  border-bottom: 1px solid #e9ecef;
  font-size: 0.95rem;
}

.restocking-table tbody tr:hover {
  background: #f8f9fa;
}

.restocking-table tbody tr.selected-row {
  background: #e7f3ff;
}

.checkbox-col {
  width: 40px;
  text-align: center;
}

.table-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.image-col {
  width: 80px;
  text-align: center;
  padding: 0.5rem;
}

.product-image {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #dee2e6;
  background: #f8f9fa;
}

.number-col {
  text-align: right;
}

.sku-col {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #495057;
}

.product-col {
  font-weight: 500;
  color: #212529;
}

.product-link {
  color: #0d6efd;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.product-link:hover {
  color: #0a58ca;
  text-decoration: underline;
}

.stock-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  background: #d1ecf1;
  color: #0c5460;
  font-weight: 600;
  font-size: 0.85rem;
}

.stock-badge.low-stock {
  background: #f8d7da;
  color: #721c24;
}

.quantity-input {
  width: 80px;
  padding: 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  text-align: right;
  font-size: 0.9rem;
}

.quantity-input:focus {
  outline: none;
  border-color: #0d6efd;
}

.total-col {
  font-weight: 600;
  color: #28a745;
}

.restocking-table tfoot {
  background: #f8f9fa;
  border-top: 2px solid #dee2e6;
}

.totals-row td {
  padding: 1.25rem 1rem;
  font-size: 1.05rem;
}

.total-label {
  text-align: right;
}

.output-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.order-button {
  flex: 1;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #28a745 0%, #20883c 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.order-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
}

.order-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reset-button.secondary {
  flex: 0 0 auto;
  background: #6c757d;
}

.reset-button.secondary:hover {
  background: #5a6268;
}

/* Responsive */
@media (max-width: 768px) {
  .ai-agent-page {
    padding: 1rem;
  }

  .agent-container {
    padding: 1.5rem;
  }

  .page-header h1 {
    font-size: 1.5rem;
  }

  .hero-section h2 {
    font-size: 1.5rem;
  }

  .features {
    flex-direction: column;
    gap: 1rem;
  }
}
</style>
