<template>
  <footer class="footer">
    <div class="container">
      <div class="footer-content">
        <div class="footer-section">
          <p class="footer-description">
            Your destination for Zava merchandise and accessories at popup shop locations across the United States.
          </p>
          <div class="social-links">
            <a href="#" class="social-link" aria-label="Facebook">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
              </svg>
            </a>
            <a href="#" class="social-link" aria-label="Instagram">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
              </svg>
            </a>
            <a href="#" class="social-link" aria-label="Twitter">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
              </svg>
            </a>
          </div>
        </div>

        <div class="footer-section">
          <h4 class="footer-heading">Shop</h4>
          <ul class="footer-links">
            <li><router-link to="/category/accessories">Accessories</router-link></li>
            <li><router-link to="/category/apparel-bottoms">Bottoms</router-link></li>
            <li><router-link to="/category/apparel-tops">Tops</router-link></li>
            <li><router-link to="/category/footwear">Footwear</router-link></li>
            <li><router-link to="/category/outerwear">Outerwear</router-link></li>
          </ul>
        </div>

        <div class="footer-section">
          <h4 class="footer-heading">Customer Service</h4>
          <ul class="footer-links">
            <li><a href="#" @click.prevent="showPlaceholder">Contact Us</a></li>
            <li><a href="#" @click.prevent="showPlaceholder">Shipping & Returns</a></li>
            <li><a href="#" @click.prevent="showPlaceholder">Size Guide</a></li>
            <li><a href="#" @click.prevent="showPlaceholder">FAQs</a></li>
            <li><a href="#" @click.prevent="showPlaceholder">Track Order</a></li>
          </ul>
        </div>

        <div class="footer-section">
          <h4 class="footer-heading">About</h4>
          <ul class="footer-links">
            <li><router-link to="/stores">Our Stores</router-link></li>
            <li><a href="#" @click.prevent="showPlaceholder">About Zava</a></li>
            <li><a href="#" @click.prevent="showPlaceholder">Careers</a></li>
            <li><a href="#" @click.prevent="showPlaceholder">Sustainability</a></li>
            <li><a href="#" @click.prevent="showPlaceholder">Privacy Policy</a></li>
          </ul>
        </div>

        <div class="footer-section">
          <h4 class="footer-heading">Newsletter</h4>
          <p class="newsletter-text">Subscribe to get special offers and updates</p>
          <form class="newsletter-form" @submit.prevent="handleNewsletter">
            <input 
              type="email" 
              placeholder="Enter your email" 
              class="newsletter-input"
              v-model="email"
            />
            <button type="submit" class="newsletter-btn">Subscribe</button>
          </form>
        </div>
      </div>

      <div class="footer-bottom">
        <p>&copy; 2025 Zava Popup Stores. All rights reserved.</p>
        <div class="payment-methods">
          <span>We accept:</span>
          <span class="payment-icons">💳 Visa • Mastercard • AmEx • PayPal</span>
        </div>
      </div>
    </div>
  </footer>
</template>

<script>
export default {
  name: 'AppFooter',
  data() {
    return {
      email: ''
    };
  },
  methods: {
    showPlaceholder() {
      alert('This feature is coming soon!');
    },
    handleNewsletter() {
      if (this.email) {
        alert('Newsletter subscription - Coming soon!');
        this.email = '';
      }
    }
  }
};
</script>

<style scoped>
.footer {
  background: var(--primary-color);
  color: white;
  padding: 3rem 0 1rem;
  margin-top: 4rem;
}

.footer-content {
  display: grid;
  grid-template-columns: 2fr repeat(4, 1fr);
  gap: 2rem;
  margin-bottom: 2rem;
}

.footer-title {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  margin-bottom: 1rem;
}

.footer-logo {
  margin-bottom: 1rem;
}

.footer-description {
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.social-links {
  display: flex;
  gap: 1rem;
}

.social-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transition: all 0.3s;
}

.social-link:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.footer-heading {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.footer-links {
  list-style: none;
}

.footer-links li {
  margin-bottom: 0.75rem;
}

.footer-links a {
  color: rgba(255, 255, 255, 0.8);
  transition: color 0.2s;
}

.footer-links a:hover {
  color: white;
}

.newsletter-text {
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.newsletter-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.newsletter-input {
  padding: 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 0.9rem;
}

.newsletter-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.newsletter-input:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.15);
}

.newsletter-btn {
  padding: 0.75rem;
  background: white;
  color: var(--primary-color);
  border-radius: 4px;
  font-weight: 600;
  transition: background 0.2s;
}

.newsletter-btn:hover {
  background: rgba(255, 255, 255, 0.9);
}

.footer-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.875rem;
}

.payment-methods {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.payment-icons {
  color: rgba(255, 255, 255, 0.8);
}

/* Responsive */
@media (max-width: 968px) {
  .footer-content {
    grid-template-columns: 1fr;
  }

  .footer-bottom {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
}

@media (max-width: 640px) {
  .footer {
    padding: 2rem 0 1rem;
  }

  .payment-methods {
    flex-direction: column;
  }
}
</style>
