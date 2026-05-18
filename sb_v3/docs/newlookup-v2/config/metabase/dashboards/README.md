# Metabase Dashboards Configuration

This directory contains YAML configuration files for Metabase dashboards.

## 📁 Files

| File | Dashboard | Description |
|------|-----------|-------------|
| `001_overview.yml` | 📊 Platform Overview | Main KPIs and platform health |
| `002_users.yml` | 👥 User Analytics | User growth and behavior |
| `003_orders.yml` | 🛒 Orders Analytics | Order processing and revenue |
| `004_sellers.yml` | 🏪 Sellers Analytics | Seller performance |
| `005_support.yml` | 🎧 Support & Disputes | Support tickets and disputes |
| `006_finances.yml` | 💰 Finances & Ledger | Financial metrics |
| `007_products.yml` | 📦 Products Catalog | Product inventory |
| `008_bots.yml` | 🤖 Bots Monitoring | Bot instances activity |

## 🔧 How to Import

### Method 1: Manual Creation (Recommended for first-time)

1. Open Metabase at http://localhost:3000
2. Go to **Browse** → **Collections**
3. Click **New Collection** → Name: "NewLookup Analytics"
4. For each YAML file:
   - Open the file and review the SQL queries
   - Create questions manually using the SQL
   - Add questions to a dashboard
   - Arrange cards according to position settings

### Method 2: Metabase API (Automated)

```bash
#!/bin/bash
# Import dashboards via Metabase API

METABASE_URL="http://localhost:3000"
USERNAME="admin@newlookup.com"
PASSWORD="your-password"

# 1. Get session ID
SESSION_ID=$(curl -s -X POST "$METABASE_URL/api/session" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.id')

# 2. Create collection
COLLECTION_ID=$(curl -s -X POST "$METABASE_URL/api/collection" \
  -H "Content-Type: application/json" \
  -H "X-Metabase-Session: $SESSION_ID" \
  -d '{"name":"NewLookup Analytics","description":"Analytics dashboards for NewLookup platform"}' \
  | jq -r '.id')

echo "Created collection: $COLLECTION_ID"

# 3. Import each dashboard
for dashboard_file in config/metabase/dashboards/001_*.yml; do
  echo "Importing $dashboard_file..."
  # Parse YAML and create dashboard via API
  # (Implementation depends on your YAML parser)
done
```

### Method 3: Metabase CLI Tool

```bash
# Install mbcli (Metabase CLI)
pip install mbcli

# Configure
mbcli configure --url http://localhost:3000 --username admin --password your-password

# Import dashboard
mbcli dashboard import config/metabase/dashboards/001_overview.yml
```

## 📊 Dashboard Structure

Each YAML file follows this structure:

```yaml
dashboard:
  name: "📊 Dashboard Name"
  description: "Description of what this dashboard shows"
  position: 1  # Order in collection
  
  parameters:
    - name: "Date Range"
      type: "date/range"
      default: "last30days"
    - name: "Filter Name"
      type: "string"
      required: false
  
  cards:
    - name: "Card Name"
      type: "number|line|bar|pie|table|heatmap|gauge|funnel|histogram|area"
      position: 
        row: 1
        col: 1
        size: 3  # 1-12 (full width is 12)
      query: |
        SELECT your_sql_query
        FROM your_table
        WHERE conditions
      visualization:
        type: "scalar"
        show-trend: true
```

## 🎨 Visualization Types

| Type | Use Case | Example |
|------|----------|---------|
| `number` | KPIs, metrics | Total Users, Revenue |
| `line` | Trends over time | Revenue Trend |
| `bar` | Comparisons | Revenue by Category |
| `pie` | Proportions | Orders by Status |
| `table` | Detailed data | Recent Orders |
| `heatmap` | Activity patterns | Orders by Hour/Day |
| `gauge` | Single metric vs target | Avg Processing Time |
| `funnel` | Conversion stages | Order Status Funnel |
| `histogram` | Distribution | Price Distribution |
| `area` | Cumulative trends | User Growth |

## 📐 Position Grid

The dashboard uses a 12-column grid:

```
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │ 8 │ 9 │10 │11 │12 │
├───┴───┴───┼───┴───┴───┼───┴───┴───┼───┴───┴───┤
│  size=3   │  size=3   │  size=3   │  size=3   │
├───────────┴───────────┼───────────┴───────────┤
│      size=6           │      size=6           │
└───────────────────────┴───────────────────────┘
```

## 🔗 Parameters

Available parameter types:

```yaml
# Date Range
- name: "Date Range"
  type: "date/range"
  default: "last30days"

# Date (single)
- name: "Start Date"
  type: "date/single"
  default: "today"

# String/Text
- name: "Category"
  type: "string"
  required: false

# Number
- name: "Min Amount"
  type: "number"
  default: 0

# Dropdown
- name: "Status"
  type: "string"
  values: ["pending", "processing", "completed"]
  required: false

# Boolean
- name: "Active Only"
  type: "boolean"
  default: true
```

## 🧪 Testing Queries

Before importing, test your SQL queries:

```sql
-- Test in Metabase SQL editor or psql
SELECT 
  DATE(created_at) as date,
  COUNT(*) as count
FROM orders
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;
```

## 📝 Best Practices

1. **Use Parameters**: Make dashboards interactive with date range and filters
2. **Optimize Queries**: Add LIMIT, use indexes, avoid SELECT *
3. **Consistent Naming**: Use emojis for visual distinction
4. **Logical Grouping**: Group related cards together
5. **Mobile-Friendly**: Design for smaller screens (use smaller sizes)
6. **Cache Settings**: Enable caching for expensive queries
7. **Documentation**: Add descriptions to all cards

## 🔐 Permissions

Set appropriate permissions for each dashboard:

```yaml
# In Metabase UI:
Dashboard → ... → Sharing → Permissions
- All users: View
- Admins: Edit
- Sellers: View (filtered to their data only)
```

## 📧 Subscriptions

Configure automated email reports:

```yaml
# For each dashboard:
Dashboard → ... → Subscriptions
- Add recipients
- Schedule: Daily at 9 AM UTC
- Format: Link + CSV attachment
```

## 🚨 Alerts

Set up alerts for critical metrics:

```yaml
# Example: Low stock alert
Card → ... → Alerts → Add alert
- Condition: stock_quantity < 10
- Send to: seller_support@newlookup.com
- Frequency: Once per hour
```

## 📊 Example: Creating First Card

1. **Open Metabase** → New → Question
2. **Select Database**: NewLookup Production
3. **Choose Mode**: Native Query (SQL)
4. **Enter SQL**:
   ```sql
   SELECT COUNT(*) as total_users
   FROM users
   WHERE created_at >= {{date_range.start}} AND created_at <= {{date_range.end}}
   ```
5. **Variable Settings**:
   - Variable name: `date_range.start`
   - Type: Date
   - Required: Yes
6. **Visualize**: Choose "Number" visualization
7. **Save**: Name: "Total Users", Collection: "NewLookup Analytics"
8. **Add to Dashboard**: Select or create dashboard

---

**Created**: March 25, 2026  
**Dashboards**: 8 configured  
**Status**: Ready for import  
