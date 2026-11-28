// Integration layer with the future backend.
// All requests go through one function; when API_BASE is empty or the
// server is unavailable, callers fall back to local data / WhatsApp.
const AppAPI = (function () {
  const baseUrl = () => (window.APP_CONFIG.API_BASE || '').replace(/\/+$/, '');

  async function request(path, options) {
    options = options || {};
    const res = await fetch(baseUrl() + path, {
      method: options.method || 'GET',
      headers: Object.assign({ 'Content-Type': 'application/json' }, options.headers || {}),
      body: options.body ? JSON.stringify(options.body) : undefined
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* empty body */ }
    if (!res.ok) {
      const err = new Error((data && data.detail) || res.statusText || 'Request failed');
      err.status = res.status;
      err.detail = data && data.detail;
      throw err;
    }
    return data;
  }

  return {
    enabled: function () { return !!baseUrl(); },

    getRestaurants: function () { return request('/api/restaurants'); },
    getRestaurant: function (id) { return request('/api/restaurants/' + encodeURIComponent(id)); },
    getPromos: function () { return request('/api/promos'); },
    validatePromo: function (code) {
      return request('/api/promos/validate?code=' + encodeURIComponent(code));
    },
    // payload: {restaurant_id, promo_code, client:{name,phone,address,comment}, items:[{item_id,qty}]}
    createOrder: function (payload) {
      return request('/api/orders', { method: 'POST', body: payload });
    },
    getOrder: function (id) { return request('/api/orders/' + encodeURIComponent(id)); }
  };
})();
