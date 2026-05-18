# React Admin Panel — Full Component Specification (v24)

This document provides the complete, copy-ready React component code for the Newlookup Admin Panel. The design follows the DaisySMS aesthetic: dense, dark, minimal whitespace.

---

## 1. Project Structure (Frontend)

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          # Axios instance with auth headers
│   │   ├── users.ts
│   │   ├── orders.ts
│   │   ├── products.ts
│   │   └── finance.ts
│   ├── components/
│   │   ├── common/
│   │   │   ├── StatCard.tsx
│   │   │   ├── DataTable.tsx
│   │   │   ├── FilterBar.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Badge.tsx
│   │   ├── users/
│   │   │   ├── UserTable.tsx
│   │   │   └── UserDetailModal.tsx
│   │   ├── orders/
│   │   │   ├── OrderTable.tsx
│   │   │   └── OrderDetailModal.tsx
│   │   ├── finance/
│   │   │   └── FinanceDashboard.tsx
│   │   └── disputes/
│   │       └── DisputeTable.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Users.tsx
│   │   ├── Orders.tsx
│   │   ├── Finance.tsx
│   │   ├── Disputes.tsx
│   │   ├── Coupons.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── useUsers.ts
│   │   ├── useOrders.ts
│   │   └── useStats.ts
│   ├── store/
│   │   └── authStore.ts       # Zustand store for auth state
│   ├── styles/
│   │   └── globals.css        # Dark theme, DaisySMS-inspired
│   └── App.tsx
```

---

## 2. API Client

### `frontend/src/api/client.ts`

```typescript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Inject auth token from localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers['X-Admin-Token'] = token;
  }
  return config;
});

// Handle 401 errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

---

## 3. Common Components

### `frontend/src/components/common/StatCard.tsx`

```tsx
import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  icon?: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, change, changeType, icon }) => {
  const changeColor =
    changeType === 'increase' ? 'text-green-400' :
    changeType === 'decrease' ? 'text-red-400' :
    'text-gray-400';

  const changeArrow = changeType === 'increase' ? '↑' : changeType === 'decrease' ? '↓' : '';

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col gap-1">
      <div className="text-gray-400 text-xs uppercase tracking-wider">
        {icon && <span className="mr-1">{icon}</span>}
        {title}
      </div>
      <div className="text-white text-2xl font-bold">{value}</div>
      {change !== undefined && (
        <div className={`text-xs ${changeColor}`}>
          {changeArrow} {Math.abs(change)}% vs yesterday
        </div>
      )}
    </div>
  );
};

export default StatCard;
```

### `frontend/src/components/common/DataTable.tsx`

```tsx
import React from 'react';

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  isLoading?: boolean;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}

function DataTable<T extends { id: number | string }>({
  columns,
  data,
  isLoading = false,
  onRowClick,
  emptyMessage = 'No data found.',
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400" />
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left text-gray-300">
        <thead className="text-xs text-gray-400 uppercase bg-gray-900 border-b border-gray-700">
          <tr>
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className="px-3 py-2 font-medium"
                style={{ width: col.width }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="text-center py-8 text-gray-500">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={row.id}
                className={`border-b border-gray-800 hover:bg-gray-750 transition-colors ${
                  onRowClick ? 'cursor-pointer' : ''
                }`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col) => (
                  <td key={String(col.key)} className="px-3 py-2">
                    {col.render
                      ? col.render(row)
                      : String((row as any)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
```

### `frontend/src/components/common/Badge.tsx`

```tsx
import React from 'react';

type BadgeVariant = 'success' | 'danger' | 'warning' | 'info' | 'neutral';

interface BadgeProps {
  label: string;
  variant: BadgeVariant;
}

const variantStyles: Record<BadgeVariant, string> = {
  success: 'bg-green-900 text-green-300 border border-green-700',
  danger: 'bg-red-900 text-red-300 border border-red-700',
  warning: 'bg-yellow-900 text-yellow-300 border border-yellow-700',
  info: 'bg-blue-900 text-blue-300 border border-blue-700',
  neutral: 'bg-gray-800 text-gray-300 border border-gray-600',
};

const Badge: React.FC<BadgeProps> = ({ label, variant }) => (
  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${variantStyles[variant]}`}>
    {label}
  </span>
);

export default Badge;
```

### `frontend/src/components/common/Modal.tsx`

```tsx
import React, { useEffect } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  width?: string;
}

const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, width = 'max-w-lg' }) => {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className={`relative bg-gray-800 border border-gray-700 rounded-lg shadow-xl ${width} w-full mx-4`}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <h3 className="text-white font-semibold">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
};

export default Modal;
```

---

## 4. User Management Components

### `frontend/src/components/users/UserTable.tsx`

```tsx
import React, { useState } from 'react';
import DataTable from '../common/DataTable';
import Badge from '../common/Badge';
import UserDetailModal from './UserDetailModal';

interface User {
  id: number;
  telegram_id: number;
  username: string;
  balance: number;
  roles: string;
  is_banned: boolean;
  created_at: string;
}

interface UserTableProps {
  users: User[];
  isLoading: boolean;
}

const UserTable: React.FC<UserTableProps> = ({ users, isLoading }) => {
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const columns = [
    { key: 'id', header: 'ID', width: '60px' },
    {
      key: 'username',
      header: 'Username',
      render: (row: User) => (
        <span className="text-blue-400">@{row.username || 'N/A'}</span>
      ),
    },
    {
      key: 'balance',
      header: 'Balance',
      render: (row: User) => (
        <span className="text-green-400 font-mono">${row.balance.toFixed(2)}</span>
      ),
    },
    {
      key: 'roles',
      header: 'Roles',
      render: (row: User) => (
        <span className="text-xs text-gray-400">{row.roles.replace(/,/g, ' ')}</span>
      ),
    },
    {
      key: 'is_banned',
      header: 'Status',
      render: (row: User) => (
        <Badge
          label={row.is_banned ? 'Banned' : 'Active'}
          variant={row.is_banned ? 'danger' : 'success'}
        />
      ),
    },
    {
      key: 'created_at',
      header: 'Registered',
      render: (row: User) => (
        <span className="text-gray-400 text-xs">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      ),
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        data={users}
        isLoading={isLoading}
        onRowClick={setSelectedUser}
        emptyMessage="No users found."
      />
      {selectedUser && (
        <UserDetailModal
          user={selectedUser}
          onClose={() => setSelectedUser(null)}
        />
      )}
    </>
  );
};

export default UserTable;
```

### `frontend/src/components/users/UserDetailModal.tsx`

```tsx
import React, { useState } from 'react';
import Modal from '../common/Modal';
import apiClient from '../../api/client';

interface User {
  id: number;
  telegram_id: number;
  username: string;
  balance: number;
  roles: string;
  is_banned: boolean;
}

interface UserDetailModalProps {
  user: User;
  onClose: () => void;
}

const UserDetailModal: React.FC<UserDetailModalProps> = ({ user, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [banReason, setBanReason] = useState('');
  const [balanceAmount, setBalanceAmount] = useState('');
  const [balanceReason, setBalanceReason] = useState('');

  const handleBan = async () => {
    if (!banReason.trim()) return;
    setLoading(true);
    try {
      await apiClient.post(`/admin/users/${user.id}/ban`, { reason: banReason });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleUnban = async () => {
    setLoading(true);
    try {
      await apiClient.post(`/admin/users/${user.id}/unban`);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleBalanceAdjust = async () => {
    if (!balanceAmount || !balanceReason.trim()) return;
    setLoading(true);
    try {
      await apiClient.post(`/admin/users/${user.id}/balance`, {
        amount: parseFloat(balanceAmount),
        reason: balanceReason,
      });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen title={`User #${user.id} — @${user.username}`} onClose={onClose} width="max-w-xl">
      <div className="space-y-4 text-sm text-gray-300">
        {/* User Info */}
        <div className="grid grid-cols-2 gap-2 bg-gray-900 p-3 rounded">
          <div><span className="text-gray-500">Telegram ID:</span> {user.telegram_id}</div>
          <div><span className="text-gray-500">Balance:</span> <span className="text-green-400">${user.balance.toFixed(2)}</span></div>
          <div><span className="text-gray-500">Roles:</span> {user.roles}</div>
          <div><span className="text-gray-500">Status:</span> {user.is_banned ? '🚫 Banned' : '✅ Active'}</div>
        </div>

        {/* Balance Adjustment */}
        <div>
          <h4 className="text-white font-medium mb-2">Adjust Balance</h4>
          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Amount (+ or -)"
              value={balanceAmount}
              onChange={(e) => setBalanceAmount(e.target.value)}
              className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-white text-xs"
            />
            <input
              type="text"
              placeholder="Reason"
              value={balanceReason}
              onChange={(e) => setBalanceReason(e.target.value)}
              className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-white text-xs"
            />
            <button
              onClick={handleBalanceAdjust}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs"
            >
              Apply
            </button>
          </div>
        </div>

        {/* Ban/Unban */}
        {user.is_banned ? (
          <button
            onClick={handleUnban}
            disabled={loading}
            className="w-full bg-green-700 hover:bg-green-600 text-white py-2 rounded text-xs"
          >
            ✅ Unban User
          </button>
        ) : (
          <div>
            <h4 className="text-white font-medium mb-2">Ban User</h4>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Ban reason"
                value={banReason}
                onChange={(e) => setBanReason(e.target.value)}
                className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-white text-xs"
              />
              <button
                onClick={handleBan}
                disabled={loading || !banReason.trim()}
                className="bg-red-700 hover:bg-red-600 text-white px-3 py-1 rounded text-xs disabled:opacity-50"
              >
                🚫 Ban
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default UserDetailModal;
```

---

## 5. Dashboard Page

### `frontend/src/pages/Dashboard.tsx`

```tsx
import React from 'react';
import StatCard from '../components/common/StatCard';
import { useStats } from '../hooks/useStats';

const Dashboard: React.FC = () => {
  const { stats, isLoading } = useStats();

  if (isLoading) {
    return <div className="text-gray-400 p-4">Loading dashboard...</div>;
  }

  return (
    <div className="p-4 space-y-6">
      <h1 className="text-white text-xl font-bold">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          title="Total Users"
          value={stats?.total_users?.toLocaleString() ?? '—'}
          icon="👥"
        />
        <StatCard
          title="Orders Today"
          value={stats?.total_orders_today?.toLocaleString() ?? '—'}
          icon="📦"
        />
        <StatCard
          title="Revenue Today"
          value={`$${(stats?.total_revenue_today ?? 0).toFixed(2)}`}
          icon="💰"
          change={stats?.revenue_change_percent}
          changeType={stats?.revenue_change_percent > 0 ? 'increase' : 'decrease'}
        />
        <StatCard
          title="Active Products"
          value={stats?.active_products?.toLocaleString() ?? '—'}
          icon="🏪"
        />
      </div>

      {/* Recent Activity placeholder */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <h2 className="text-white font-semibold mb-3">Recent Orders</h2>
        <p className="text-gray-500 text-sm">Load recent orders table here...</p>
      </div>
    </div>
  );
};

export default Dashboard;
```

---

## 6. Users Page

### `frontend/src/pages/Users.tsx`

```tsx
import React, { useState } from 'react';
import UserTable from '../components/users/UserTable';
import { useUsers } from '../hooks/useUsers';

const Users: React.FC = () => {
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [bannedFilter, setBannedFilter] = useState('');

  const { users, isLoading, refetch } = useUsers({
    search,
    role: roleFilter || undefined,
    is_banned: bannedFilter === 'banned' ? true : bannedFilter === 'active' ? false : undefined,
  });

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-white text-xl font-bold">Users</h1>
        <span className="text-gray-400 text-sm">{users?.length ?? 0} found</span>
      </div>

      {/* Filter Bar */}
      <div className="flex gap-2 flex-wrap">
        <input
          type="text"
          placeholder="Search by username or ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-white text-sm w-64"
        />
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-white text-sm"
        >
          <option value="">All Roles</option>
          <option value="buyer">Buyer</option>
          <option value="seller">Seller</option>
          <option value="support">Support</option>
          <option value="moderator">Moderator</option>
          <option value="admin">Admin</option>
        </select>
        <select
          value={bannedFilter}
          onChange={(e) => setBannedFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-white text-sm"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="banned">Banned</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        <UserTable users={users ?? []} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default Users;
```

---

## 7. Coupons Page (Owner Only)

### `frontend/src/pages/Coupons.tsx`

```tsx
import React, { useState } from 'react';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import Badge from '../components/common/Badge';
import apiClient from '../api/client';

interface Coupon {
  id: number;
  code: string;
  discount_percent: number;
  max_uses: number;
  use_count: number;
  is_active: boolean;
}

const Coupons: React.FC = () => {
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCoupon, setNewCoupon] = useState({ code: '', discount_percent: 10, max_uses: 1 });

  const fetchCoupons = async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get('/coupons/');
      setCoupons(res.data);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    await apiClient.post('/coupons/', newCoupon);
    setShowCreateModal(false);
    fetchCoupons();
  };

  const handleDelete = async (id: number) => {
    await apiClient.delete(`/coupons/${id}`);
    fetchCoupons();
  };

  const columns = [
    { key: 'id', header: 'ID', width: '60px' },
    { key: 'code', header: 'Code', render: (row: Coupon) => <code className="text-yellow-400">{row.code}</code> },
    { key: 'discount_percent', header: 'Discount', render: (row: Coupon) => `${row.discount_percent}%` },
    { key: 'use_count', header: 'Uses', render: (row: Coupon) => `${row.use_count} / ${row.max_uses}` },
    {
      key: 'is_active',
      header: 'Status',
      render: (row: Coupon) => (
        <Badge label={row.is_active ? 'Active' : 'Inactive'} variant={row.is_active ? 'success' : 'neutral'} />
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row: Coupon) => (
        <button
          onClick={(e) => { e.stopPropagation(); handleDelete(row.id); }}
          className="text-red-400 hover:text-red-300 text-xs"
        >
          Delete
        </button>
      ),
    },
  ];

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-white text-xl font-bold">Coupons</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded text-sm"
        >
          + Create Coupon
        </button>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        <DataTable columns={columns} data={coupons} isLoading={isLoading} />
      </div>

      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Create Coupon">
        <div className="space-y-3">
          <div>
            <label className="text-gray-400 text-xs block mb-1">Coupon Code</label>
            <input
              type="text"
              value={newCoupon.code}
              onChange={(e) => setNewCoupon({ ...newCoupon, code: e.target.value.toUpperCase() })}
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-white text-sm"
              placeholder="e.g. SUMMER20"
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Discount %</label>
            <input
              type="number"
              value={newCoupon.discount_percent}
              onChange={(e) => setNewCoupon({ ...newCoupon, discount_percent: Number(e.target.value) })}
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-white text-sm"
              min={1} max={100}
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">Max Uses</label>
            <input
              type="number"
              value={newCoupon.max_uses}
              onChange={(e) => setNewCoupon({ ...newCoupon, max_uses: Number(e.target.value) })}
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-white text-sm"
              min={1}
            />
          </div>
          <button
            onClick={handleCreate}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded text-sm"
          >
            Create
          </button>
        </div>
      </Modal>
    </div>
  );
};

export default Coupons;
```

---

## 8. Global Styles

### `frontend/src/styles/globals.css`

```css
/* DaisySMS-inspired dark theme */
:root {
  --bg-primary: #0f1117;
  --bg-secondary: #1a1d27;
  --bg-card: #1e2130;
  --border-color: #2d3148;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --accent-blue: #3b82f6;
  --accent-green: #22c55e;
  --accent-red: #ef4444;
  --accent-yellow: #eab308;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'Inter', 'SF Pro Display', -apple-system, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #4a5568; }

/* Table hover */
.bg-gray-750 { background-color: #252836; }
```
