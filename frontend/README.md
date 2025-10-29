# Zava Popup Store - Frontend

A modern, responsive Vue.js frontend for the Zava popup clothing store demo.

## Features

- 🛍️ Product catalog with categories and subcategories
- 🏪 Store location finder
- 📱 Fully responsive design
- 🎨 Modern, clean UI with smooth animations
- 🔄 Real product data from backend API
- 📦 Mock checkout and cart functionality

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── assets/         # Styles and images
│   ├── components/     # Reusable Vue components
│   │   ├── AppHeader.vue
│   │   ├── AppFooter.vue
│   │   └── ProductCard.vue
│   ├── views/          # Page components
│   │   ├── HomePage.vue
│   │   ├── CategoryPage.vue
│   │   ├── ProductPage.vue
│   │   └── StoresPage.vue
│   ├── router/         # Vue Router configuration
│   ├── services/       # API services
│   ├── config/         # Configuration files
│   ├── App.vue         # Root component
│   └── main.js         # Application entry point
├── index.html
├── vite.config.js
└── package.json
```

## Tech Stack

- **Vue 3** - Progressive JavaScript framework
- **Vue Router** - Official routing library
- **Axios** - HTTP client for API calls
- **Vite** - Next-generation frontend tooling

## Getting Started

### Prerequisites

- Node.js 16+ and npm

### Installation

```bash
cd frontend
npm install
```

### Configuration

The API base URL can be configured via environment variable:

Create a `.env` file in the `frontend` directory:

```
VITE_API_BASE_URL=http://localhost:8091
```

Or modify `src/config/api.js` directly.

### Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

Built files will be in the `dist/` directory.

## API Integration

The frontend expects a REST API with the following endpoints:

- `GET /api/categories` - Get all product categories
- `GET /api/products` - Get all products
- `GET /api/products/category/:category` - Get products by category
- `GET /api/products/featured` - Get featured products
- `GET /api/products/:id` - Get product details

## Product Images

Product images should be placed in `public/images/products/` with filenames matching product IDs:
- `/images/products/{product_id}.jpg`

A placeholder image will be shown if product image is not found.

## Categories

The store includes the following main categories:

1. **Accessories** - Bags, Belts, Caps, Gloves, Scarves, Socks, Sunglasses
2. **Bottoms** - Jeans, Pants, Shorts
3. **Tops** - Flannel, Formal Shirts, Hoodies, Sweatshirts, T-Shirts
4. **Footwear** - Boots, Dress Shoes, Sandals, Sneakers
5. **Outerwear** - Coats, Jackets

## Notes

This is a demo frontend designed to showcase a realistic retail UI. Several features are mocked/placeholder:
- Cart functionality
- Checkout process
- User authentication
- Payment processing
- Search functionality

The focus is on demonstrating AI-powered procurement features in the backend rather than a fully functional e-commerce system.
