// Global application configuration.
// No secrets are stored here — only public runtime settings.
window.APP_CONFIG = {
  // Backend API base URL. Empty string = API disabled, the site runs on
  // local data from data.js and orders go through WhatsApp (fallback).
  // Example when the backend is running: 'http://localhost:8000'
  API_BASE: '',

  // Order fallback channel (public business number).
  WHATSAPP_NUMBER: '992009553795',

  // Delivery pricing (смн).
  DELIVERY_FEE: 5,
  // Free delivery is applied automatically when the subtotal reaches this value.
  FREE_DELIVERY_THRESHOLD: 100,

  CURRENCY: 'смн',

  // Promo codes (kept in sync with the backend when API_BASE is set).
  PROMOS: [
    { code: 'SALE10', percent: 10, active: true }
  ],

  STORAGE_KEYS: {
    cart: 'tezraspj_cart_v1',
    theme: 'tezraspj_theme_v1'
  }
};
