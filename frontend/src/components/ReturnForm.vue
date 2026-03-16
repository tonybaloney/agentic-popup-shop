<template>
  <div class="return-overlay" @click.self="$emit('close')">
    <div class="return-form-container">
      <!-- Header -->
      <div class="return-header">
        <h2>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
          </svg>
          Return Products
        </h2>
        <button class="close-btn" @click="$emit('close')" aria-label="Close">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Step Indicator -->
      <div class="step-indicator">
        <div class="step" :class="{ active: step === 1, complete: step > 1 }">
          <span class="step-num">1</span>
          <span class="step-label">Select Items</span>
        </div>
        <div class="step-divider" :class="{ active: step > 1 }"></div>
        <div class="step" :class="{ active: step === 2, complete: step > 2 }">
          <span class="step-num">2</span>
          <span class="step-label">Upload Photo</span>
        </div>
        <div class="step-divider" :class="{ active: step > 2 }"></div>
        <div class="step" :class="{ active: step === 3 }">
          <span class="step-num">3</span>
          <span class="step-label">Result</span>
        </div>
      </div>

      <!-- Step 1: Select Return Type & Items -->
      <div v-if="step === 1" class="return-step">
        <div class="form-group">
          <label>Return Type</label>
          <div class="return-type-selector">
            <button
              class="type-btn"
              :class="{ selected: returnType === 'full' }"
              @click="returnType = 'full'"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              </svg>
              <span>Full Order Return</span>
              <small>Return all items in the order</small>
            </button>
            <button
              class="type-btn"
              :class="{ selected: returnType === 'partial' }"
              @click="returnType = 'partial'"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
              </svg>
              <span>Partial Return</span>
              <small>Return specific items only</small>
            </button>
          </div>
        </div>

        <!-- Item selection for partial returns -->
        <div v-if="returnType === 'partial'" class="form-group">
          <label>Select items to return:</label>
          <div class="item-list">
            <div
              v-for="item in order.items"
              :key="item.order_item_id"
              class="return-item"
              :class="{ selected: selectedItems.includes(item.order_item_id) }"
            >
              <label class="item-checkbox">
                <input
                  type="checkbox"
                  :value="item.order_item_id"
                  v-model="selectedItems"
                  @change="initReturnQuantity(item)"
                />
                <div class="item-image">
                  <img
                    v-if="item.image_url"
                    :src="`/images/products/${item.image_url}`"
                    :alt="item.product_name"
                  />
                  <div v-else class="placeholder-img">📦</div>
                </div>
                <div class="item-info">
                  <div class="item-name">{{ item.product_name }}</div>
                  <div class="item-meta">
                    SKU: {{ item.sku }} · Ordered: {{ item.quantity }} ·
                    ${{ (item.unit_price || item.total_amount / item.quantity).toFixed(2) }} each
                  </div>
                </div>
              </label>
              <!-- Quantity selector (visible when item is checked and qty > 1) -->
              <div
                v-if="selectedItems.includes(item.order_item_id) && item.quantity > 1"
                class="qty-selector"
              >
                <label class="qty-label">Return qty:</label>
                <button
                  class="qty-btn"
                  :disabled="(returnQuantities[item.order_item_id] || 1) <= 1"
                  @click.prevent="adjustQty(item, -1)"
                >−</button>
                <span class="qty-value">{{ returnQuantities[item.order_item_id] || 1 }}</span>
                <button
                  class="qty-btn"
                  :disabled="(returnQuantities[item.order_item_id] || 1) >= item.quantity"
                  @click.prevent="adjustQty(item, 1)"
                >+</button>
                <span class="qty-of">of {{ item.quantity }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Reason -->
        <div class="form-group">
          <label for="return-reason">Reason for return</label>
          <textarea
            id="return-reason"
            v-model="reason"
            rows="3"
            placeholder="Please tell us why you'd like to return..."
          ></textarea>
          <p class="policy-hint">
            Please provide a reason covered by our
            <a href="/returns-policy.html" target="_blank" rel="noopener">Returns Policy</a>.
            Eligible reasons include defective items, wrong item received, size issues, and more.
          </p>
        </div>

        <div class="form-actions">
          <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
          <button
            class="btn btn-primary"
            :disabled="!canProceed"
            @click="goToStep2"
          >
            Continue
          </button>
        </div>
      </div>

      <!-- Step 2: Photo Upload (full) or Confirmation (partial) -->
      <div v-if="step === 2" class="return-step">
        <!-- Photo upload (required for all returns) -->
        <div class="photo-upload-section">
          <h3>📸 Photo Verification Required</h3>
          <p class="upload-instructions">
            Please upload a photo showing <strong>the items you are returning</strong>.
            Our AI will verify the photo matches your return request before processing.
          </p>

          <div
            class="upload-area"
            :class="{ 'has-image': photoPreview, dragover: isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="$refs.fileInput.click()"
          >
            <input
              ref="fileInput"
              type="file"
              accept="image/*"
              @change="handleFileSelect"
              class="file-input"
            />
            <div v-if="!photoPreview" class="upload-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
              <p>Click or drag a photo here</p>
              <small>JPG, PNG — automatically compressed for upload</small>
            </div>
            <div v-else class="image-preview">
              <img :src="photoPreview" alt="Return photo preview" />
              <button class="remove-photo" @click.stop="removePhoto">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Items summary for partial returns -->
        <div v-if="returnType === 'partial'" class="confirmation-section">
          <h3>Items Being Returned</h3>
          <div class="confirm-items">
            <div v-for="item in itemsToReturn" :key="item.order_item_id" class="confirm-item">
              <span class="item-name">{{ item.product_name }}</span>
              <span class="item-qty">Qty: {{ item.returnQty ?? item.quantity }}</span>
              <span class="item-price">${{ ((item.unit_price || item.total_amount / item.quantity) * (item.returnQty ?? item.quantity)).toFixed(2) }}</span>
            </div>
          </div>
          <div class="confirm-total">
            <span>Estimated Refund</span>
            <span class="total-amount">${{ estimatedRefund.toFixed(2) }}</span>
          </div>
          <p class="confirm-reason" v-if="reason">
            <strong>Reason:</strong> {{ reason }}
          </p>
        </div>

        <div class="form-actions">
          <button class="btn btn-secondary" @click="step = 1">Back</button>
          <button
            class="btn btn-primary"
            :disabled="!photoFile"
            @click="submitReturn"
          >
            <span v-if="!submitting">Submit Return</span>
            <span v-else class="loading-text">
              <span class="spinner-sm"></span> Processing...
            </span>
          </button>
        </div>
      </div>

      <!-- Step 3: Result -->
      <div v-if="step === 3" class="return-step result-step">
        <div v-if="result" class="result-card" :class="{ approved: result.approved, denied: !result.approved }">
          <div class="result-icon">
            <svg v-if="result.approved" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <svg v-else width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
          </div>
          <h3>{{ result.approved ? 'Return Approved!' : 'Return Not Approved' }}</h3>
          <p class="result-summary">{{ result.summary }}</p>

          <div v-if="result.approved" class="result-details">
            <div class="detail-row" v-if="result.refund_amount > 0">
              <span>Refund Amount</span>
              <span class="detail-value">${{ result.refund_amount.toFixed(2) }}</span>
            </div>
            <div class="detail-row">
              <span>Return Type</span>
              <span class="detail-value">{{ result.return_type === 'full' ? 'Full Order' : 'Partial' }}</span>
            </div>
            <div class="detail-row" v-if="result.photo_verified">
              <span>Photo Verified</span>
              <span class="detail-value verified">✓ Verified</span>
            </div>
          </div>
        </div>

        <div v-if="submitError" class="error-card">
          <p>{{ submitError }}</p>
        </div>

        <div class="form-actions">
          <button class="btn btn-primary" @click="$emit('close')">Done</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { authStore } from '../stores/auth';

export default {
  name: 'ReturnForm',
  props: {
    order: {
      type: Object,
      required: true,
    },
  },
  emits: ['close', 'return-submitted'],
  data() {
    return {
      step: 1,
      returnType: 'full',
      selectedItems: [],
      returnQuantities: {},
      reason: '',
      photoFile: null,
      photoPreview: null,
      isDragging: false,
      submitting: false,
      result: null,
      submitError: null,
    };
  },
  computed: {
    canProceed() {
      if (this.returnType === 'partial') {
        return this.selectedItems.length > 0;
      }
      return true;
    },
    itemsToReturn() {
      if (this.returnType === 'full') {
        return this.order.items;
      }
      return this.order.items
        .filter((item) => this.selectedItems.includes(item.order_item_id))
        .map((item) => ({
          ...item,
          returnQty: this.returnQuantities[item.order_item_id] || item.quantity,
        }));
    },
    estimatedRefund() {
      return this.itemsToReturn.reduce((sum, item) => {
        const unitPrice = item.unit_price || item.total_amount / item.quantity;
        const qty = item.returnQty ?? item.quantity;
        return sum + unitPrice * qty;
      }, 0);
    },
  },
  methods: {
    initReturnQuantity(item) {
      // When an item is checked, default return qty to the full ordered quantity
      if (this.selectedItems.includes(item.order_item_id)) {
        this.returnQuantities = {
          ...this.returnQuantities,
          [item.order_item_id]: item.quantity,
        };
      }
    },
    adjustQty(item, delta) {
      const current = this.returnQuantities[item.order_item_id] || item.quantity;
      const next = Math.max(1, Math.min(item.quantity, current + delta));
      this.returnQuantities = {
        ...this.returnQuantities,
        [item.order_item_id]: next,
      };
    },
    goToStep2() {
      this.step = 2;
    },
    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) this.setPhoto(file);
    },
    handleDrop(event) {
      this.isDragging = false;
      const file = event.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        this.setPhoto(file);
      }
    },
    setPhoto(file) {
      this.compressImage(file).then((compressed) => {
        this.photoFile = compressed;
        const reader = new FileReader();
        reader.onload = (e) => {
          this.photoPreview = e.target.result;
        };
        reader.readAsDataURL(compressed);
      });
    },
    compressImage(file, maxDimension = 1280, quality = 0.7, maxBytes = 1024 * 1024) {
      return new Promise((resolve) => {
        // Skip non-image files
        if (!file.type.startsWith('image/')) {
          resolve(file);
          return;
        }
        // Already small enough — skip compression
        if (file.size <= maxBytes) {
          resolve(file);
          return;
        }
        const img = new Image();
        const url = URL.createObjectURL(file);
        img.onload = () => {
          URL.revokeObjectURL(url);
          let { width, height } = img;

          // Scale down preserving aspect ratio
          if (width > height) {
            if (width > maxDimension) {
              height = Math.round(height * (maxDimension / width));
              width = maxDimension;
            }
          } else {
            if (height > maxDimension) {
              width = Math.round(width * (maxDimension / height));
              height = maxDimension;
            }
          }

          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);

          // Iteratively lower quality until under maxBytes
          const tryCompress = (q) => {
            canvas.toBlob(
              (blob) => {
                if (blob.size > maxBytes && q > 0.3) {
                  tryCompress(q - 0.1);
                } else {
                  const compressed = new File([blob], file.name.replace(/\.\w+$/, '.jpg'), {
                    type: 'image/jpeg',
                    lastModified: Date.now(),
                  });
                  resolve(compressed);
                }
              },
              'image/jpeg',
              q,
            );
          };
          tryCompress(quality);
        };
        img.onerror = () => {
          URL.revokeObjectURL(url);
          resolve(file); // Fall back to original on error
        };
        img.src = url;
      });
    },
    removePhoto() {
      this.photoFile = null;
      this.photoPreview = null;
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
    },
    async submitReturn() {
      this.submitting = true;
      this.submitError = null;

      try {
        const token = authStore.getToken();
        if (!token) throw new Error('Not authenticated');

        const formData = new FormData();
        formData.append('order_id', this.order.order_id);
        formData.append('return_type', this.returnType);
        formData.append('reason', this.reason);

        // Add items for partial returns
        const items = this.itemsToReturn.map((item) => ({
          product_name: item.product_name,
          sku: item.sku,
          quantity: item.returnQty ?? item.quantity,
        }));
        formData.append('items_json', JSON.stringify(items));

        // Add photo
        if (this.photoFile) {
          formData.append('photo', this.photoFile);
        }

        const response = await fetch('/api/returns', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || err.error || `HTTP ${response.status}`);
        }

        this.result = await response.json();
        this.step = 3;
        this.$emit('return-submitted', this.result);
      } catch (err) {
        this.submitError = err.message || 'Failed to submit return. Please try again.';
        this.step = 3;
      } finally {
        this.submitting = false;
      }
    },
  },
};
</script>

<style scoped>
.return-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.return-form-container {
  background: var(--color-background, #fff);
  border-radius: 12px;
  width: 100%;
  max-width: 640px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.return-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border, #e5e7eb);
}

.return-header h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1.25rem;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--color-text-secondary, #6b7280);
  border-radius: 4px;
}

.close-btn:hover {
  background: var(--color-background-hover, #f3f4f6);
}

/* Step Indicator */
.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem 1.5rem;
  gap: 0.5rem;
}

.step {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  background: var(--color-background-hover, #e5e7eb);
  color: var(--color-text-secondary, #6b7280);
}

.step.active .step-num {
  background: var(--color-primary, #3b82f6);
  color: white;
}

.step.complete .step-num {
  background: #10b981;
  color: white;
}

.step-label {
  font-size: 0.8rem;
  color: var(--color-text-secondary, #6b7280);
}

.step.active .step-label {
  color: var(--color-text, #111827);
  font-weight: 600;
}

.step-divider {
  flex: 1;
  height: 2px;
  background: var(--color-border, #e5e7eb);
  max-width: 60px;
}

.step-divider.active {
  background: #10b981;
}

/* Form Steps */
.return-step {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.875rem;
  resize: vertical;
  box-sizing: border-box;
}

.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary, #3b82f6);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.policy-hint {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--color-text-muted, #6b7280);
  line-height: 1.4;
}

.policy-hint a {
  color: var(--color-primary, #3b82f6);
  text-decoration: underline;
  font-weight: 500;
}

.policy-hint a:hover {
  color: var(--color-primary-hover, #2563eb);
}

/* Return type selector */
.return-type-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.type-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  padding: 1rem;
  border: 2px solid var(--color-border, #d1d5db);
  border-radius: 10px;
  background: var(--color-background, #fff);
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn:hover {
  border-color: var(--color-primary, #3b82f6);
}

.type-btn.selected {
  border-color: var(--color-primary, #3b82f6);
  background: rgba(59, 130, 246, 0.05);
}

.type-btn span {
  font-weight: 600;
  font-size: 0.875rem;
}

.type-btn small {
  color: var(--color-text-secondary, #6b7280);
  font-size: 0.75rem;
}

/* Item list */
.item-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.return-item {
  border: 2px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  transition: all 0.2s;
}

.return-item.selected {
  border-color: var(--color-primary, #3b82f6);
  background: rgba(59, 130, 246, 0.03);
}

.item-checkbox {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  cursor: pointer;
}

.item-checkbox input[type='checkbox'] {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary, #3b82f6);
}

.item-image {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder-img {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-background-hover, #f3f4f6);
  font-size: 1.25rem;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-weight: 600;
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  font-size: 0.75rem;
  color: var(--color-text-secondary, #6b7280);
  margin-top: 2px;
}

/* Quantity selector */
.qty-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem 0.75rem 3.5rem;
}

.qty-label {
  font-size: 0.8rem;
  color: var(--color-text-secondary, #6b7280);
  margin-right: 0.25rem;
}

.qty-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--color-border, #d1d5db);
  background: var(--color-background, #fff);
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.qty-btn:hover:not(:disabled) {
  background: var(--color-background-hover, #f3f4f6);
}

.qty-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.qty-value {
  font-weight: 600;
  font-size: 0.9rem;
  min-width: 1.5rem;
  text-align: center;
}

.qty-of {
  font-size: 0.75rem;
  color: var(--color-text-secondary, #6b7280);
}

/* Photo upload */
.photo-upload-section h3 {
  margin: 0 0 0.5rem;
}

.upload-instructions {
  color: var(--color-text-secondary, #6b7280);
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.upload-area {
  border: 2px dashed var(--color-border, #d1d5db);
  border-radius: 10px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 1rem;
}

.upload-area:hover,
.upload-area.dragover {
  border-color: var(--color-primary, #3b82f6);
  background: rgba(59, 130, 246, 0.03);
}

.upload-area.has-image {
  padding: 0.5rem;
  border-style: solid;
}

.file-input {
  display: none;
}

.upload-placeholder p {
  margin: 0.5rem 0 0.25rem;
  font-weight: 600;
}

.upload-placeholder small {
  color: var(--color-text-secondary, #6b7280);
}

.upload-placeholder svg {
  color: var(--color-text-secondary, #9ca3af);
}

.image-preview {
  position: relative;
}

.image-preview img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
}

.remove-photo {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  border: none;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

/* Confirmation section */
.confirmation-section h3 {
  margin: 0 0 1rem;
}

.confirm-items {
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.confirm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border, #e5e7eb);
}

.confirm-item:last-child {
  border-bottom: none;
}

.confirm-item .item-name {
  flex: 1;
  font-weight: 500;
}

.confirm-item .item-qty {
  color: var(--color-text-secondary, #6b7280);
  font-size: 0.875rem;
  margin: 0 1rem;
}

.confirm-item .item-price {
  font-weight: 600;
}

.confirm-total {
  display: flex;
  justify-content: space-between;
  padding: 1rem;
  background: var(--color-background-hover, #f9fafb);
  border-radius: 8px;
  font-weight: 600;
}

.total-amount {
  color: var(--color-primary, #3b82f6);
  font-size: 1.125rem;
}

.confirm-reason {
  margin-top: 0.75rem;
  font-size: 0.875rem;
  color: var(--color-text-secondary, #6b7280);
}

/* Result */
.result-step {
  text-align: center;
}

.result-card {
  padding: 2rem 1.5rem;
}

.result-icon {
  margin-bottom: 1rem;
}

.result-card.approved .result-icon {
  color: #10b981;
}

.result-card.denied .result-icon {
  color: #ef4444;
}

.result-card h3 {
  margin: 0 0 0.75rem;
  font-size: 1.25rem;
}

.result-card.approved h3 {
  color: #10b981;
}

.result-card.denied h3 {
  color: #ef4444;
}

.result-summary {
  color: var(--color-text-secondary, #6b7280);
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.result-details {
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
  text-align: left;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border, #e5e7eb);
  font-size: 0.875rem;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-value {
  font-weight: 600;
}

.detail-value.verified {
  color: #10b981;
}

.error-card {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 1rem;
  color: #dc2626;
  margin-bottom: 1rem;
}

/* Actions */
.form-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border, #e5e7eb);
}

.btn {
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--color-primary, #3b82f6);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--color-background-hover, #f3f4f6);
  color: var(--color-text, #374151);
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
