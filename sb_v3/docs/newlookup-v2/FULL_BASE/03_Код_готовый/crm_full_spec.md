# CRM Full Specification

This document provides a complete specification for the Customer Relationship Management (CRM) module within the Admin Panel.

---

## 1. Overview

The CRM is the central hub for managing all users of the Newlookup platform. It provides a 360-degree view of each user, including their roles, activity, transactions, and support history. Access is role-based.

## 2. Roles & Permissions

| Role      | Can View All Users | Can Edit Users | Can View Finances | Can Ban Users |
| :-------- | :----------------- | :------------- | :---------------- | :------------ |
| `owner`   | ✅ Yes             | ✅ Yes         | ✅ Yes            | ✅ Yes        |
| `admin`   | ✅ Yes             | ✅ Yes         | ✅ Yes            | ✅ Yes        |
| `moderator`| ✅ Yes             | ✅ Yes (limited) | ❌ No             | ✅ Yes        |
| `support` | ✅ Yes             | ❌ No          | ❌ No             | ❌ No         |
| `finance` | ✅ Yes (read-only) | ❌ No          | ✅ Yes (read-only)| ❌ No         |

## 3. Main User List View

This is the default view of the CRM.

```
--------------------------------------------------------------------------
| 👥 CRM - All Users (1,234)     | [Search by ID/Username...] [Filter ▼] |
--------------------------------------------------------------------------
|                                                                        |
| [ ] User ID | Username      | Roles         | Balance  | Last Seen      |
|------------------------------------------------------------------------|
| [ ] 123     | @testuser1    | Buyer, Seller | $150.00  | 5 min ago      |
| [ ] 124     | @testuser2    | Buyer         | $25.50   | 2 hours ago    |
| [ ] 125     | @testuser3    | Marketer      | $0.00    | 1 day ago      |
|                                                                        |
--------------------------------------------------------------------------
| [Ban Selected] [Send Message] [Export] | Page 1 of 124 | [ < ] [ > ]   |
--------------------------------------------------------------------------
```

**Filters:**
- By Role (Buyer, Seller, Marketer, Worker)
- By Balance (e.g., > $100)
- By Last Seen (e.g., within 24 hours)
- By Ban Status (Banned / Not Banned)

## 4. User 360° Profile View

Clicking on a user opens their detailed profile.

```
--------------------------------------------------------------------------
| 👤 Profile: @testuser1 (ID: 123) | [Ban User] [Login as User] [Send Msg] |
--------------------------------------------------------------------------
|                                                                        |
| [Overview] [Purchase History] [Sales] [Transactions] [Support Tickets] |
|------------------------------------------------------------------------|
|                                                                        |
| **User Details**                                                       |
|   - Username: @testuser1                                               |
|   - Roles: Buyer, Seller                                               |
|   - Balance: $150.00                                                   |
|   - Trust Score: 85/100                                                |
|   - Joined: 2026-01-15                                                 |
|   - Last Seen: 5 minutes ago                                           |
|                                                                        |
| **Recent Activity**                                                    |
|   - Viewed product #567                                                |
|   - Made purchase #9876                                                |
|   - Opened support ticket #456                                         |
|                                                                        |
--------------------------------------------------------------------------
```

### 4.1. Purchase History Tab

Lists all purchases made by the user.

### 4.2. Sales Tab

If the user is a seller, lists all their sales.

### 4.3. Transactions Tab

Lists all financial transactions (deposits, withdrawals, purchases, refunds).

### 4.4. Support Tickets Tab

Lists all support tickets created by the user, with their current status.

---

## 5. Full RBAC Matrix (v24)

This is the definitive role-permission matrix for the entire Newlookup system. All bots, APIs, and Admin Panel must enforce these permissions.

| Permission | `buyer` | `seller` | `marketer` | `worker` | `support` | `finance` | `moderator` | `admin` | `owner` |
|---|---|---|---|---|---|---|---|---|---|
| View own profile | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Purchase products | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Open dispute | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Create/edit own products | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Create marketing bots | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Fulfill per-order tasks | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| View order details + buyer username | ❌ | ❌ | ❌ | ✅ (own orders) | ✅ | ❌ | ✅ | ✅ | ✅ |
| View all users (CRM) | ❌ | ❌ | ❌ | ❌ | ✅ (read-only) | ✅ (read-only) | ✅ | ✅ | ✅ |
| Edit user profile | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (limited) | ✅ | ✅ |
| Edit product price (audit logged) | ❌ | ✅ (own) | ❌ | ❌ | ✅ (with reason) | ❌ | ✅ | ✅ | ✅ |
| Ban/unban users | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| View all transactions | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Approve/reject withdrawals | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Create balance adjustments | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (audit logged) | ❌ | ✅ | ✅ |
| View financial reports | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Create coupons | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| View audit logs | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Change system settings | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage staff roles | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Notes:**
- `worker` sees order details and buyer username ONLY for orders assigned to them.
- `support` can edit product price but MUST provide a reason, which is logged in `audit_logs`.
- `finance` is a formal role separate from `admin`. Read-only financial access + withdrawal approval.
- All `admin` and `finance` actions on financial data are logged in `audit_logs`.

---

## 6. Staff Management Panel

```
--------------------------------------------------------------------------
| 👥 Staff Management                     | [+ Add Staff Member]          |
--------------------------------------------------------------------------
| User ID | Username      | Role(s)        | Added By | Added At         |
|---------|---------------|----------------|----------|------------------|
| 456     | @support_anna | support        | @owner   | 2026-01-20       |
| 789     | @finance_bob  | finance        | @owner   | 2026-02-01       |
| 101     | @mod_charlie  | moderator      | @admin   | 2026-02-15       |
--------------------------------------------------------------------------
```

Only `owner` can assign `admin` role. `admin` can assign `support`, `finance`, `moderator`, `worker` roles.

---

## 7. Audit Log Viewer

```
--------------------------------------------------------------------------
| 📋 Audit Log                            | [Filter by Actor] [Filter by Action] |
--------------------------------------------------------------------------
| Timestamp           | Actor     | Action              | Target           |
|---------------------|-----------|---------------------|------------------|
| 2026-03-13 14:00:05 | @admin1   | ban_user            | User #123        |
| 2026-03-13 13:55:12 | @support1 | edit_product_price  | Product #456 → $99.99 |
| 2026-03-13 13:50:00 | @finance1 | approve_withdrawal  | Withdrawal #789  |
--------------------------------------------------------------------------
```

The audit log is **immutable** — no entries can be edited or deleted, even by the owner.
