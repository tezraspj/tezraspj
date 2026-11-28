// tezraspj — application logic (UI, cart, checkout).
// Depends on: config.js (APP_CONFIG), data.js (restaurants), api.js (AppAPI).
(function () {
  'use strict';

  const CFG = window.APP_CONFIG;
  const qs = id => document.getElementById(id);

  // ---------- State ----------
  let currentRestaurant = null;
  let cart = [];                 // [{id, name, price, image, qty}]
  let cartRestaurantId = null;   // cart belongs to exactly one restaurant
  let cartRestaurantName = '';
  let discountPercent = 0;
  let appliedPromoCode = '';
  let activeCategory = 'Все';
  let activeRestCat = 'all';

  // ---------- Persistence ----------
  function saveCart() {
    try {
      localStorage.setItem(CFG.STORAGE_KEYS.cart, JSON.stringify({
        items: cart,
        restaurantId: cartRestaurantId,
        restaurantName: cartRestaurantName,
        discountPercent: discountPercent,
        promoCode: appliedPromoCode
      }));
    } catch (e) { /* storage unavailable (private mode) — ignore */ }
  }

  function loadCart() {
    try {
      const raw = localStorage.getItem(CFG.STORAGE_KEYS.cart);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || !Array.isArray(data.items)) return;
      cart = data.items.filter(i => i && i.id && i.name && typeof i.price === 'number' && i.qty > 0);
      cartRestaurantId = data.restaurantId || null;
      cartRestaurantName = data.restaurantName || '';
      discountPercent = Number(data.discountPercent) || 0;
      appliedPromoCode = data.promoCode || '';
      if (discountPercent > 0 && appliedPromoCode) {
        const input = qs('promoCodeInput');
        if (input) input.value = appliedPromoCode;
      }
      // Cart must not outlive its restaurant.
      if (cart.length && (!cartRestaurantId || !restaurants.some(r => r.id === cartRestaurantId))) {
        clearCart(false);
      }
    } catch (e) { /* corrupted storage — ignore */ }
  }

  function clearCart(render) {
    cart = [];
    cartRestaurantId = null;
    cartRestaurantName = '';
    discountPercent = 0;
    appliedPromoCode = '';
    const input = qs('promoCodeInput');
    if (input) input.value = '';
    saveCart();
    if (render !== false) updateCartUI();
  }

  // ---------- Totals (single source of truth) ----------
  function computeTotals() {
    let subtotal = 0;
    let totalQty = 0;
    cart.forEach(item => {
      subtotal += item.price * item.qty;
      totalQty += item.qty;
    });
    // Free delivery automatically when the threshold is reached.
    let deliveryFee = 0;
    if (cart.length > 0) {
      deliveryFee = subtotal >= CFG.FREE_DELIVERY_THRESHOLD ? 0 : CFG.DELIVERY_FEE;
    }
    const discount = (subtotal * discountPercent) / 100;
    const total = subtotal > 0 ? subtotal - discount + deliveryFee : 0;
    return { subtotal, totalQty, deliveryFee, discount, total };
  }

  // ---------- Restaurants ----------
  function renderRestaurants(category) {
    activeRestCat = category || 'all';
    const grid = qs('restaurantsGrid');
    const q = (qs('searchInput').value || '').trim().toLowerCase();

    let list = activeRestCat === 'all'
      ? restaurants
      : restaurants.filter(r => r.category === activeRestCat);

    if (q) list = list.filter(r => (r.name + ' ' + r.description).toLowerCase().includes(q));

    if (!list.length) {
      grid.innerHTML = '<div class="empty"><span>🔍</span><p>Ничего не найдено</p><small>Попробуйте изменить запрос или фильтр</small></div>';
      return;
    }

    grid.innerHTML = list.map((r, i) => `
      <article class="rcard anim" style="--d:${i * 60}ms" data-restaurant="${r.id}" role="button" tabindex="0">
        <div class="rcard__media">
          <img src="${r.image}" alt="${r.name}" loading="lazy">
          <span class="rcard__index">${String(i + 1).padStart(2, '0')}</span>
          <span class="rcard__rating">★ ${r.rating}</span>
        </div>
        <div class="rcard__body">
          <h3>${r.name}</h3>
          <p>${r.description}</p>
          <div class="rcard__meta">
            <div class="rcard__facts"><span>⏱ ${r.deliveryTime}</span><span>Мин. ${r.minOrder}</span></div>
            <span class="rcard__cta">Меню →</span>
          </div>
        </div>
      </article>`).join('');
  }

  function filterRestaurants(cat, btnElement) {
    document.querySelectorAll('.rest-cat-btn').forEach(b => b.classList.remove('active'));
    if (btnElement) btnElement.classList.add('active');
    renderRestaurants(cat);
  }

  function openRestaurantMenu(id) {
    currentRestaurant = restaurants.find(r => r.id === id);
    if (!currentRestaurant) return;
    qs('restaurantsView').classList.add('hidden');
    qs('menuView').classList.remove('hidden');
    qs('searchInput').value = '';

    qs('restaurantHeader').innerHTML = `
      <img src="${currentRestaurant.image}" alt="${currentRestaurant.name}">
      <div class="rhead__info">
        <span class="rhead__label">Меню заведения</span>
        <h1>${currentRestaurant.name}</h1>
        <p>${currentRestaurant.description}</p>
        <div class="rhead__stats">
          <span class="star">★ ${currentRestaurant.rating}</span>
          <span>⏱ ${currentRestaurant.deliveryTime}</span>
          <span>🛍 Мин. ${currentRestaurant.minOrder}</span>
        </div>
      </div>`;

    const categories = ['Все', ...new Set(currentRestaurant.menu.map(item => item.category))];
    qs('menuCategoryFilter').innerHTML = categories.map((c, idx) => `
      <button data-menu-cat="${idx}" class="chip menu-cat-btn ${idx === 0 ? 'active' : ''}">
        ${c}
      </button>`).join('');
    qs('menuCategoryFilter').querySelectorAll('.menu-cat-btn').forEach((btn, idx) => {
      btn.addEventListener('click', () => filterMenuItems(categories[idx], btn));
    });

    activeCategory = 'Все';
    renderMenuItems('Все');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function renderMenuItems(cat) {
    const grid = qs('menuGrid');
    if (!currentRestaurant) return;

    const q = (qs('searchInput').value || '').trim().toLowerCase();
    let items = cat === 'Все'
      ? currentRestaurant.menu
      : currentRestaurant.menu.filter(i => i.category === cat);

    if (q) items = items.filter(i => i.name.toLowerCase().includes(q));

    if (!items.length) {
      grid.innerHTML = '<div class="empty"><span>🔍</span><p>Ничего не найдено</p><small>Попробуйте другой запрос</small></div>';
      return;
    }

    grid.innerHTML = items.map((item, i) => `
      <article class="mcard anim" style="--d:${Math.min(i, 8) * 50}ms">
        <div class="mcard__media"><img src="${item.image}" alt="${item.name}" loading="lazy"></div>
        <div class="mcard__body">
          <h4>${item.name}</h4>
          <p>${item.description}</p>
          <div class="mcard__row">
            <span class="price">${item.price}<i>${CFG.CURRENCY}</i></span>
            <button data-add="${item.id}" class="btn-add" aria-label="Добавить в корзину">+</button>
          </div>
        </div>
      </article>`).join('');
  }

  function filterMenuItems(cat, btnElement) {
    activeCategory = cat;
    document.querySelectorAll('.menu-cat-btn').forEach(b => b.classList.remove('active'));
    if (btnElement) btnElement.classList.add('active');
    renderMenuItems(cat);
  }

  function handleSearch() {
    const menuOpen = !qs('menuView').classList.contains('hidden');
    if (menuOpen) renderMenuItems(activeCategory);
    else renderRestaurants(activeRestCat);
  }

  function showRestaurantsView() {
    qs('menuView').classList.add('hidden');
    qs('restaurantsView').classList.remove('hidden');
    qs('searchInput').value = '';
    renderRestaurants(activeRestCat);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ---------- Cart ----------
  function addToCart(itemId) {
    if (!currentRestaurant) return;
    const item = currentRestaurant.menu.find(i => i.id === itemId);
    if (!item) return;

    // One order = one restaurant. Mixing is not allowed.
    if (cart.length && cartRestaurantId && cartRestaurantId !== currentRestaurant.id) {
      const ok = window.confirm(
        'В корзине блюда из ресторана «' + cartRestaurantName + '».\n' +
        'Добавить блюда из «' + currentRestaurant.name + '»? Корзина будет очищена.'
      );
      if (!ok) return;
      cart = [];
      discountPercent = 0;
      appliedPromoCode = '';
      qs('promoCodeInput').value = '';
    }

    cartRestaurantId = currentRestaurant.id;
    cartRestaurantName = currentRestaurant.name;

    const existing = cart.find(c => c.id === itemId);
    if (existing) existing.qty += 1;
    else cart.push({ id: item.id, name: item.name, price: item.price, image: item.image, qty: 1 });

    saveCart();
    updateCartUI();
  }

  function updateCartQty(id, delta) {
    const item = cart.find(c => c.id === id);
    if (item) {
      item.qty += delta;
      if (item.qty <= 0) cart = cart.filter(c => c.id !== id);
    }
    if (!cart.length) {
      cartRestaurantId = null;
      cartRestaurantName = '';
    }
    saveCart();
    updateCartUI();
  }

  function removeCartItem(id) {
    cart = cart.filter(c => c.id !== id);
    if (!cart.length) {
      cartRestaurantId = null;
      cartRestaurantName = '';
    }
    saveCart();
    updateCartUI();
  }

  function updateCartUI() {
    const list = qs('cartItemsList');
    const t = computeTotals();

    if (!cart.length) {
      list.innerHTML = '<div class="cart__empty"><span>🛒</span><p>Корзина пуста</p><small>Добавьте блюда из меню заведения</small></div>';
    } else {
      list.innerHTML = cart.map(item => `
        <div class="citem">
          <img src="${item.image}" alt="${item.name}">
          <div class="citem__info">
            <h5>${item.name}</h5>
            <span class="citem__price">${item.price * item.qty} ${CFG.CURRENCY} · ${item.qty} шт</span>
            <button class="citem__remove" data-remove="${item.id}" aria-label="Удалить позицию">✕</button>
          </div>
          <div class="qty">
            <button data-qty="${item.id}" data-delta="-1" aria-label="Убрать одну">−</button>
            <span>${item.qty}</span>
            <button data-qty="${item.id}" data-delta="1" aria-label="Добавить одну">+</button>
          </div>
        </div>`).join('');
    }

    const badge = qs('cartCountBadge');
    badge.innerText = t.totalQty;
    badge.classList.remove('bump');
    void badge.offsetWidth;
    badge.classList.add('bump');

    qs('cartSubtotal').innerText = `${t.subtotal} ${CFG.CURRENCY}`;
    const feeEl = qs('cartDeliveryFee');
    feeEl.innerText = t.deliveryFee === 0 ? '0 ' + CFG.CURRENCY : `${t.deliveryFee} ${CFG.CURRENCY}`;
    feeEl.closest('.totals__row').classList.toggle('free', cart.length > 0 && t.deliveryFee === 0);
    qs('cartDiscount').innerText = `-${Math.round(t.discount * 100) / 100} ${CFG.CURRENCY}`;
    qs('cartTotal').innerText = `${Math.round(t.total * 100) / 100} ${CFG.CURRENCY}`;
    qs('discountRow').classList.toggle('show', t.discount > 0);

    // Free delivery hint.
    const hint = qs('deliveryHint');
    if (hint) {
      if (!cart.length) {
        hint.textContent = '';
        hint.className = 'delivery-hint';
      } else if (t.deliveryFee === 0) {
        hint.textContent = 'Бесплатная доставка применена ✓';
        hint.className = 'delivery-hint ok';
      } else {
        hint.textContent = `До бесплатной доставки: ${Math.round((CFG.FREE_DELIVERY_THRESHOLD - t.subtotal) * 100) / 100} ${CFG.CURRENCY}`;
        hint.className = 'delivery-hint';
      }
    }

    // Restaurant name in cart header.
    const restEl = qs('cartRestaurant');
    if (restEl) {
      restEl.textContent = cartRestaurantName ? '🏪 ' + cartRestaurantName : '';
      restEl.classList.toggle('hidden', !cartRestaurantName);
    }
  }

  function toggleCartSidebar() {
    const open = qs('cartSidebar').classList.toggle('open');
    qs('cartOverlay').classList.toggle('open', open);
    document.body.style.overflow = open ? 'hidden' : '';
  }

  // ---------- Promo ----------
  function findLocalPromo(code) {
    return (CFG.PROMOS || []).find(p => p.active !== false && p.code.toUpperCase() === code) || null;
  }

  async function applyPromoCode() {
    const input = qs('promoCodeInput');
    const code = input.value.trim().toUpperCase();
    if (!code) { alert('Введите промокод'); return; }

    let promo = null;
    if (AppAPI.enabled()) {
      try {
        const res = await AppAPI.validatePromo(code);
        if (res && res.valid) promo = { code: code, percent: res.percent };
      } catch (e) { /* server unavailable — use local list */ }
    }
    if (!promo) promo = findLocalPromo(code);

    if (promo) {
      discountPercent = promo.percent;
      appliedPromoCode = promo.code;
      input.value = promo.code;
      saveCart();
      alert(`Промокод ${promo.code}: скидка ${promo.percent}% применена!`);
    } else {
      discountPercent = 0;
      appliedPromoCode = '';
      saveCart();
      alert('Неверный промокод');
    }
    updateCartUI();
  }

  // ---------- Checkout validation ----------
  function validateForm() {
    const fields = [
      { el: qs('clientName'), label: 'Имя', test: v => /^[A-Za-zА-Яа-яЁёғқҷҳҒҚҷҲ\s'-]{2,50}$/.test(v), msg: 'Имя: 2–50 букв (допустимы пробелы и дефис)' },
      { el: qs('clientPhone'), label: 'Телефон', test: isValidPhone, msg: 'Телефон: +992 XX XXX XXX (или 9XXXXXXXXX)' },
      { el: qs('clientAddress'), label: 'Адрес', test: v => v.length >= 5 && v.length <= 200, msg: 'Адрес: от 5 символов (улица, дом, ориентир)' }
    ];
    let firstBad = null;
    fields.forEach(f => {
      const value = f.el.value.trim();
      const ok = f.test(value);
      f.el.classList.toggle('field--error', !ok);
      if (!ok && !firstBad) firstBad = f;
    });
    if (firstBad) {
      alert(firstBad.msg);
      firstBad.el.focus();
      return false;
    }
    const comment = qs('clientComment');
    if (comment.value.length > 500) {
      comment.classList.add('field--error');
      alert('Комментарий: не более 500 символов');
      comment.focus();
      return false;
    }
    comment.classList.remove('field--error');
    return true;
  }

  function isValidPhone(value) {
    const digits = value.replace(/\D/g, '');
    if (digits.startsWith('992') && digits.length === 12) return true;   // +992XXXXXXXXX
    if (digits.length === 9 && /^[2-9]/.test(digits)) return true;       // 9XXXXXXXX (local)
    if (digits.length === 10 && digits.startsWith('8')) return true;     // 8XXXXXXXXX
    if (digits.length === 9 && value.trim().startsWith('+992')) return true;
    return /^\+992\s?\d{2}\s?\d{3}\s?\d{3}$/.test(value.trim());
  }

  // ---------- Checkout ----------
  async function checkoutWhatsApp() {
    if (cart.length === 0) {
      alert('Ваша корзина пуста! Добавьте товары из меню.');
      return;
    }
    if (!validateForm()) return;

    const name = qs('clientName').value.trim();
    const phone = qs('clientPhone').value.trim();
    const address = qs('clientAddress').value.trim();
    const comment = qs('clientComment').value.trim();
    const t = computeTotals();

    const payload = {
      restaurant_id: cartRestaurantId,
      promo_code: appliedPromoCode || null,
      client: { name: name, phone: phone, address: address, comment: comment },
      items: cart.map(c => ({ item_id: c.id, qty: c.qty }))
    };

    // Try the backend first (it re-checks prices and totals server-side).
    if (AppAPI.enabled()) {
      try {
        const order = await AppAPI.createOrder(payload);
        alert(`Заказ №${order.id} принят! Статус: ${order.status}.`);
        clearCart(true);
        ['clientName', 'clientPhone', 'clientAddress', 'clientComment'].forEach(id => { qs(id).value = ''; });
        toggleCartSidebar();
        return;
      } catch (e) {
        if (e.status && e.status >= 400 && e.status < 500) {
          alert('Заказ отклонён сервером: ' + (typeof e.detail === 'string' ? e.detail : 'проверьте данные'));
          return;
        }
        // Server error/offline — fall through to WhatsApp.
      }
    }

    // Fallback: order via WhatsApp (works without a backend).
    let text = `📦 *НОВЫЙ ЗАКАЗ — tezraspj (Пенджикент)*\n`;
    text += `🏪 *Заведение:* ${cartRestaurantName || 'tezraspj'}\n\n`;
    text += `👤 *Клиент:* ${name}\n`;
    text += `📞 *Телефон:* ${phone}\n`;
    text += `📍 *Адрес:* ${address}\n`;
    if (comment) text += `💬 *Комментарий:* ${comment}\n`;

    text += `\n📋 *СОСТАВ ЗАКАЗА:*\n`;
    cart.forEach((item, index) => {
      text += `${index + 1}. ${item.name} x${item.qty} = ${item.price * item.qty} ${CFG.CURRENCY}\n`;
    });

    text += `\n💵 *РАСЧЁТ:*\n`;
    text += `• Сумма товаров: ${t.subtotal} ${CFG.CURRENCY}\n`;
    if (t.discount > 0) text += `• Скидка (${appliedPromoCode}, ${discountPercent}%): -${Math.round(t.discount * 100) / 100} ${CFG.CURRENCY}\n`;
    text += `• Доставка по городу: ${t.deliveryFee === 0 ? 'бесплатно (от ' + CFG.FREE_DELIVERY_THRESHOLD + ' смн)' : t.deliveryFee + ' ' + CFG.CURRENCY}\n`;
    text += `💰 *ИТОГО К ОПЛАТЕ:* *${Math.round(t.total * 100) / 100} ${CFG.CURRENCY}*\n`;

    const url = `https://wa.me/${CFG.WHATSAPP_NUMBER}?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
    clearCart(true);
  }

  // ---------- Theme ----------
  const ICON_SUN = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  const ICON_MOON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>';

  function applyTheme(isDark) {
    document.documentElement.classList.toggle('dark', isDark);
    qs('themeIcon').innerHTML = isDark ? ICON_SUN : ICON_MOON;
    try { localStorage.setItem(CFG.STORAGE_KEYS.theme, isDark ? 'dark' : 'light'); } catch (e) { /* ignore */ }
  }

  function toggleDarkMode() {
    applyTheme(!document.documentElement.classList.contains('dark'));
  }

  // ---------- Events ----------
  function bindEvents() {
    // Restaurant cards: click + keyboard.
    qs('restaurantsGrid').addEventListener('click', e => {
      const card = e.target.closest('[data-restaurant]');
      if (card) openRestaurantMenu(card.dataset.restaurant);
    });
    qs('restaurantsGrid').addEventListener('keydown', e => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const card = e.target.closest('[data-restaurant]');
      if (card) { e.preventDefault(); openRestaurantMenu(card.dataset.restaurant); }
    });

    // Menu: add to cart.
    qs('menuGrid').addEventListener('click', e => {
      const btn = e.target.closest('[data-add]');
      if (btn) addToCart(btn.dataset.add);
    });

    // Cart: quantity + remove (event delegation replaces inline handlers).
    qs('cartItemsList').addEventListener('click', e => {
      const qtyBtn = e.target.closest('[data-qty]');
      if (qtyBtn) {
        updateCartQty(qtyBtn.dataset.qty, Number(qtyBtn.dataset.delta));
        return;
      }
      const rm = e.target.closest('[data-remove]');
      if (rm) removeCartItem(rm.dataset.remove);
    });

    // Clear field errors while typing.
    ['clientName', 'clientPhone', 'clientAddress', 'clientComment'].forEach(id => {
      qs(id).addEventListener('input', () => qs(id).classList.remove('field--error'));
    });

    // Bottom navigation active state.
    document.querySelectorAll('.bnav__item').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.bnav__item').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Anchor links inside the header should not leave a stale hash behind.
    document.querySelectorAll('.nav a').forEach(a => {
      a.addEventListener('click', () => {
        setTimeout(() => { if (location.hash) history.replaceState(null, '', location.pathname); }, 0);
      });
    });

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && qs('cartSidebar').classList.contains('open')) toggleCartSidebar();
    });

    // Expose handlers used by inline attributes in index.html.
    window.showRestaurantsView = showRestaurantsView;
    window.filterRestaurants = filterRestaurants;
    window.openRestaurantMenu = openRestaurantMenu;
    window.filterMenuItems = filterMenuItems;
    window.handleSearch = handleSearch;
    window.addToCart = addToCart;
    window.updateCartQty = updateCartQty;
    window.removeCartItem = removeCartItem;
    window.toggleCartSidebar = toggleCartSidebar;
    window.applyPromoCode = applyPromoCode;
    window.checkoutWhatsApp = checkoutWhatsApp;
    window.toggleDarkMode = toggleDarkMode;
  }

  // ---------- API bootstrap (optional) ----------
  async function initFromAPI() {
    if (!AppAPI.enabled()) return;
    try {
      const data = await AppAPI.getRestaurants();
      if (Array.isArray(data) && data.length && data[0].menu) {
        restaurants = data;
        renderRestaurants(activeRestCat);
      }
    } catch (e) { /* backend offline — keep local data */ }
    try {
      const promos = await AppAPI.getPromos();
      if (Array.isArray(promos) && promos.length) {
        CFG.PROMOS = promos.filter(p => p.active !== false);
      }
    } catch (e) { /* keep local promos */ }
  }

  // ---------- Init ----------
  document.addEventListener('DOMContentLoaded', () => {
    let theme = 'dark';
    try { theme = localStorage.getItem(CFG.STORAGE_KEYS.theme) || 'dark'; } catch (e) { /* ignore */ }
    applyTheme(theme !== 'light');

    bindEvents();
    loadCart();
    renderRestaurants('all');
    updateCartUI();
    initFromAPI();
  });
})();
