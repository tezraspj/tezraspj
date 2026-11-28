# tezraspj — доставка еды в Пенджикенте

Сайт доставки еды: заведения, меню, корзина, промокоды, оформление заказа
(WhatsApp или API), плюс готовый backend (FastAPI) и админ-панель.

Дизайн — NIMA-стиль (чёрный фон, жёлтый акцент `#FFD600`, курсивные
заголовки Archivo): визуал, карточки, анимации и мобильная навигация
сохранены, изменена только архитектура кода.

## Структура

```
public/                  статический сайт (GitHub Pages)
├── index.html           только разметка
├── css/style.css        весь дизайн + новые стили формы/корзины
├── js/config.js         публичные настройки (API_BASE, порог 100 смн, промо)
├── js/data.js           локальные данные: 8 заведений, 294 блюда (fallback)
├── js/api.js            интеграционный слой AppAPI (fetch → backend)
├── js/app.js            логика UI: корзина, итоги, промо, валидация, заказ
├── admin/               админ-панель поверх Admin API (Bearer-токен)
└── img/                 место под локальные картинки
server/                  backend (FastAPI + SQLAlchemy + Alembic + Pydantic)
├── app/                 config, db, models, schemas, security, rate_limit,
│                        telegram, pricing, routers/ (public + admin API)
├── migrations/          Alembic (0001_initial)
├── seed.py              импорт data/restaurants.json (идемпотентный)
├── requirements.txt
└── .env.example         шаблон переменных окружения
data/restaurants.json    данные для сидинга (экпорт из data.js)
tests/                   pytest-тесты API и безопасности + smoke_live.py
docs/                    аудит и план
```

## Запуск сайта (frontend)

```bash
python -m http.server 8765 --directory public
# → http://localhost:8765
```

Без backend сайт работает автономно: данные из `data.js`, заказы уходят
через WhatsApp (`wa.me/992009553795`).

## Запуск backend

```bash
cd server
pip install -r requirements.txt
cp .env.example .env              # заполнить переменные
python -m alembic upgrade head    # создать таблицы
python seed.py                    # импортировать заведения и меню
uvicorn app.main:app --port 8000
# Swagger: http://localhost:8000/docs
```

Включить API на сайте: в `public/js/config.js` укажите
`API_BASE: 'http://localhost:8000'`. Пока `API_BASE` пуст — сайт работает
на локальных данных.

## Тесты

```bash
python -m pytest tests/ -q          # 24 теста: API, цены, безопасность
python tests/smoke_live.py          # smoke-тест против запущенного сервера
```

## Возможности

- заведения с фильтрами и поиском; меню с категориями;
- корзина: количество, удаление, запрет смешивания ресторанов,
  сохранение после перезагрузки (localStorage);
- доставка 5 смн, **бесплатно от 100 смн** (подсказка до порога);
- промокоды (SALE10 = 10%), проверка на сервере;
- форма заказа: имя/телефон/адрес/комментарий с валидацией;
- backend: серверный пересчёт цен, заказы, пользователи, статусы,
  промокоды, Telegram-уведомления (best-effort);
- Admin API (Bearer `ADMIN_API_TOKEN`): рестораны, категории, меню, цены,
  заказы и статусы, промокоды; веб-админка в `public/admin/`;
- безопасность: PBKDF2, сравнение токенов constant-time, только ORM,
  rate limiting (120/min API, 10/min заказы), секреты только в .env.

## Настройка под себя

- заведения/меню — `public/js/data.js` (и `data/restaurants.json` для БД);
- доставка/порог/промо/WhatsApp — `public/js/config.js`;
- секреты и БД — `server/.env` (см. `.env.example`): `ADMIN_API_TOKEN`,
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DATABASE_URL`
  (dev: sqlite, prod: PostgreSQL).
