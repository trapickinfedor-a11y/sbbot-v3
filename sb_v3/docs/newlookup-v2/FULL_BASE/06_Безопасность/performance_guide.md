# Performance Guide — Indexes, Caching & Query Optimization (v24)

This document provides the complete performance optimization strategy for the Newlookup platform, covering database indexes, Redis caching, query optimization, and bot response time improvements.

---

## 1. Database Indexes

All indexes below must be created in the Alembic migration that creates the corresponding tables. They are critical for production performance.

### 1.1. Users Table

```sql
-- Primary lookup: find user by Telegram ID (most frequent query in the system)
CREATE UNIQUE INDEX idx_users_telegram_id ON users(telegram_id);

-- Role-based filtering for admin panel and notifications
CREATE INDEX idx_users_roles ON users USING gin(to_tsvector('simple', roles));

-- Ban status filtering
CREATE INDEX idx_users_is_banned ON users(is_banned) WHERE is_banned = TRUE;

-- Balance queries (for leaderboards, analytics)
CREATE INDEX idx_users_balance ON users(balance DESC);
```

### 1.2. Products Table

```sql
-- Category browsing (most frequent catalog query)
CREATE INDEX idx_products_category_active ON products(category_id, is_active, stock)
    WHERE is_active = TRUE AND stock > 0;

-- Seller's product management
CREATE INDEX idx_products_seller_id ON products(seller_id);

-- Price range filtering
CREATE INDEX idx_products_price ON products(price);

-- Full-text search on product titles
CREATE INDEX idx_products_title_fts ON products USING gin(to_tsvector('russian', title));
```

### 1.3. Orders Table

```sql
-- Buyer's purchase history (most frequent order query)
CREATE INDEX idx_orders_buyer_id ON orders(buyer_id, created_at DESC);

-- Seller's sales history (via product join)
CREATE INDEX idx_orders_product_id ON orders(product_id);

-- Status filtering for admin panel
CREATE INDEX idx_orders_status ON orders(status);

-- Date-range analytics queries
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
```

### 1.4. Transactions Table

```sql
-- User transaction history
CREATE INDEX idx_transactions_user_id ON transactions(user_id, created_at DESC);

-- Pending deposit processing (Celery task)
CREATE INDEX idx_transactions_type_pending ON transactions(type, created_at)
    WHERE type IN ('deposit_pending', 'withdrawal_approved');
```

### 1.5. Disputes Table

```sql
-- Support staff dispute queue
CREATE INDEX idx_disputes_status ON disputes(status, created_at DESC);

-- Order-dispute lookup (check if dispute exists for an order)
CREATE UNIQUE INDEX idx_disputes_order_id ON disputes(order_id);
```

### 1.6. Coupons Table

```sql
-- Coupon code lookup (case-insensitive)
CREATE UNIQUE INDEX idx_coupons_code ON coupons(UPPER(code));

-- Active coupon filtering
CREATE INDEX idx_coupons_active ON coupons(is_active) WHERE is_active = TRUE;
```

### 1.7. Alembic Migration Template

```python
# migrations/versions/xxxx_add_performance_indexes.py
from alembic import op

def upgrade():
    # Users
    op.create_index('idx_users_telegram_id', 'users', ['telegram_id'], unique=True)
    op.create_index('idx_users_is_banned', 'users', ['is_banned'],
                    postgresql_where="is_banned = TRUE")
    op.create_index('idx_users_balance', 'users', [sa.text('balance DESC')])

    # Products
    op.create_index('idx_products_category_active', 'products',
                    ['category_id', 'is_active', 'stock'],
                    postgresql_where="is_active = TRUE AND stock > 0")
    op.create_index('idx_products_seller_id', 'products', ['seller_id'])

    # Orders
    op.create_index('idx_orders_buyer_id', 'orders',
                    ['buyer_id', sa.text('created_at DESC')])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_created_at', 'orders', [sa.text('created_at DESC')])

    # Transactions
    op.create_index('idx_transactions_user_id', 'transactions',
                    ['user_id', sa.text('created_at DESC')])

    # Disputes
    op.create_index('idx_disputes_status', 'disputes',
                    ['status', sa.text('created_at DESC')])
    op.create_index('idx_disputes_order_id', 'disputes', ['order_id'], unique=True)

    # Coupons
    op.create_index('idx_coupons_code', 'coupons',
                    [sa.text('UPPER(code)')], unique=True)

def downgrade():
    op.drop_index('idx_users_telegram_id')
    op.drop_index('idx_users_is_banned')
    op.drop_index('idx_products_category_active')
    op.drop_index('idx_products_seller_id')
    op.drop_index('idx_orders_buyer_id')
    op.drop_index('idx_orders_status')
    op.drop_index('idx_orders_created_at')
    op.drop_index('idx_transactions_user_id')
    op.drop_index('idx_disputes_status')
    op.drop_index('idx_disputes_order_id')
    op.drop_index('idx_coupons_code')
```

---

## 2. Redis Caching Strategy

### 2.1. What to Cache

| Data | Cache Key | TTL | Invalidation Trigger |
|---|---|---|---|
| Platform stats (Dashboard) | `platform:stats` | 1 hour | Celery task recalculates hourly |
| Product catalog by category | `catalog:{category_id}` | 15 min | Product create/update/delete |
| Individual product detail | `product:{product_id}` | 15 min | Product update |
| User profile (balance, roles) | `user:{telegram_id}` | 5 min | Balance update, role change |
| Active coupons list | `coupons:active` | 30 min | Coupon create/deactivate |
| Seller daily stats | `seller:stats:{seller_id}:{date}` | 24 hours | New order for seller |

### 2.2. Caching Utility

```python
# app/utils/cache.py
import redis
import json
import functools
from typing import Any, Optional, Callable
import os

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

def cache_get(key: str) -> Optional[Any]:
    """Get a value from Redis cache. Returns None if not found."""
    value = redis_client.get(key)
    if value:
        return json.loads(value)
    return None

def cache_set(key: str, value: Any, ttl: int = 300):
    """Set a value in Redis cache with TTL in seconds."""
    redis_client.setex(key, ttl, json.dumps(value, default=str))

def cache_delete(key: str):
    """Delete a key from Redis cache."""
    redis_client.delete(key)

def cache_delete_pattern(pattern: str):
    """Delete all keys matching a pattern (use sparingly)."""
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)

def cached(key_template: str, ttl: int = 300):
    """
    Decorator for caching function results.
    key_template can include {arg_name} placeholders.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from template and arguments
            bound = func.__code__.co_varnames[:func.__code__.co_argcount]
            arg_dict = dict(zip(bound, args))
            arg_dict.update(kwargs)
            key = key_template.format(**arg_dict)

            cached_value = cache_get(key)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            cache_set(key, result, ttl)
            return result
        return wrapper
    return decorator
```

### 2.3. Caching in Services

```python
# app/services/product_service.py
from app.utils.cache import cache_get, cache_set, cache_delete

class ProductService:
    def get_products_by_category(self, category_id: int) -> list:
        """Get products with caching."""
        cache_key = f"catalog:{category_id}"
        cached = cache_get(cache_key)
        if cached:
            return cached

        products = (
            self.db.query(Product)
            .filter(
                Product.category_id == category_id,
                Product.is_active == True,
                Product.stock > 0
            )
            .order_by(Product.sort_order.asc(), Product.created_at.desc())
            .all()
        )

        result = [p.to_dict() for p in products]
        cache_set(cache_key, result, ttl=900)  # 15 minutes
        return result

    def update_product(self, product_id: int, **kwargs) -> Product:
        """Update product and invalidate cache."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        for key, value in kwargs.items():
            setattr(product, key, value)
        self.db.commit()

        # Invalidate caches
        cache_delete(f"product:{product_id}")
        cache_delete(f"catalog:{product.category_id}")
        return product

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get single product with caching."""
        cache_key = f"product:{product_id}"
        cached = cache_get(cache_key)
        if cached:
            # Reconstruct from dict (simplified)
            return cached

        product = self.db.query(Product).filter(Product.id == product_id).first()
        if product:
            cache_set(cache_key, product.to_dict(), ttl=900)
        return product
```

---

## 3. Query Optimization

### 3.1. Avoid N+1 Queries

Always use `joinedload` or `selectinload` to avoid N+1 query problems:

```python
# BAD: N+1 queries (1 query for orders + N queries for products)
orders = db.query(Order).filter(Order.buyer_id == user_id).all()
for order in orders:
    print(order.product.title)  # Each access triggers a new query

# GOOD: Single query with eager loading
from sqlalchemy.orm import joinedload

orders = (
    db.query(Order)
    .options(joinedload(Order.product).joinedload(Product.category))
    .filter(Order.buyer_id == user_id)
    .order_by(Order.created_at.desc())
    .limit(50)
    .all()
)
```

### 3.2. Pagination

Always paginate large result sets. Never return unbounded queries:

```python
# app/services/base_service.py
from sqlalchemy.orm import Query

def paginate(query: Query, page: int, per_page: int = 20):
    """
    Apply pagination to a SQLAlchemy query.
    Returns (items, total_count, total_pages).
    """
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page
    return items, total, total_pages

# Usage:
orders_query = (
    db.query(Order)
    .filter(Order.buyer_id == user_id)
    .order_by(Order.created_at.desc())
)
orders, total, pages = paginate(orders_query, page=1, per_page=20)
```

### 3.3. Select Only Required Columns

For list views, avoid loading all columns:

```python
# BAD: Loads all columns including large text fields
products = db.query(Product).all()

# GOOD: Load only what's needed for the list view
from sqlalchemy import select

result = db.execute(
    select(Product.id, Product.title, Product.price, Product.stock)
    .where(Product.category_id == category_id, Product.is_active == True)
    .order_by(Product.sort_order)
).all()
```

### 3.4. Bulk Operations

For batch inserts/updates, use bulk operations:

```python
# BAD: Individual inserts in a loop
for item in items:
    db.add(item)
    db.commit()

# GOOD: Bulk insert
db.bulk_insert_mappings(Product, [item.dict() for item in items])
db.commit()
```

---

## 4. Bot Response Time Optimization

### 4.1. Async Database Sessions

Use async SQLAlchemy for bot handlers to avoid blocking the event loop:

```python
# app/db.py (async version)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async_engine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### 4.2. Pre-build Keyboards

Build static keyboards once at startup, not on every request:

```python
# bots/mirror_bot/keyboards/static.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Built once at module import time
MAIN_MENU_KEYBOARD_RU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Каталог"), KeyboardButton(text="💼 Мой профиль")],
        [KeyboardButton(text="📦 История покупок"), KeyboardButton(text="💰 Пополнить баланс")],
        [KeyboardButton(text="🆘 Поддержка")],
    ],
    resize_keyboard=True,
)

MAIN_MENU_KEYBOARD_EN = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Catalog"), KeyboardButton(text="💼 My Profile")],
        [KeyboardButton(text="📦 Purchase History"), KeyboardButton(text="💰 Deposit")],
        [KeyboardButton(text="🆘 Support")],
    ],
    resize_keyboard=True,
)
```

### 4.3. Connection Pooling

Ensure database connections are pooled and reused:

```python
# Recommended pool settings for production
engine = create_engine(
    DATABASE_URL,
    pool_size=10,        # Maintain 10 persistent connections
    max_overflow=20,     # Allow up to 20 additional connections under load
    pool_timeout=30,     # Wait max 30s for a connection
    pool_recycle=3600,   # Recycle connections every hour (prevents stale connections)
    pool_pre_ping=True,  # Test connection before using (handles DB restarts)
)
```

---

## 5. Admin Panel Performance

### 5.1. React Query for Data Fetching

```typescript
// frontend/src/hooks/useUsers.ts
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';

interface UseUsersParams {
  search?: string;
  role?: string;
  is_banned?: boolean;
  page?: number;
}

export function useUsers(params: UseUsersParams = {}) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: async () => {
      const res = await apiClient.get('/admin/users/', { params });
      return res.data;
    },
    staleTime: 30_000,   // Consider data fresh for 30 seconds
    gcTime: 5 * 60_000,  // Keep in cache for 5 minutes
    refetchOnWindowFocus: false,
  });
}
```

### 5.2. Virtual Scrolling for Large Tables

For tables with thousands of rows, use `@tanstack/react-virtual`:

```typescript
// Use when displaying > 100 rows
import { useVirtualizer } from '@tanstack/react-virtual';

// Renders only visible rows, dramatically reducing DOM nodes
const rowVirtualizer = useVirtualizer({
  count: data.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 40, // Row height in pixels
});
```

---

## 6. Performance Monitoring

### 6.1. Slow Query Logging

```python
# app/db.py
import logging
import time
from sqlalchemy import event

slow_query_logger = logging.getLogger('slow_queries')

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.5:  # Log queries taking > 500ms
        slow_query_logger.warning(
            f"Slow query ({total:.3f}s): {statement[:200]}"
        )
```

### 6.2. Key Performance Targets

| Metric | Target | Alert Threshold |
|---|---|---|
| Bot response time (p95) | < 500ms | > 2s |
| API response time (p95) | < 200ms | > 1s |
| Catalog page load | < 300ms | > 1s |
| Purchase flow (end-to-end) | < 1s | > 3s |
| Admin panel initial load | < 2s | > 5s |
| Database query time (p95) | < 50ms | > 500ms |
| Cache hit rate | > 80% | < 60% |
