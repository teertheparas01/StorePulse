# StorePulse — Master Execution Plan & Technical Specification

> **Target Audience for this document**: Any AI coding agent or software engineer implementing StorePulse.
> **Goal**: A zero-ambiguity blueprint for building a retail management system with autonomous AI product replacement. Follow each section in sequence.

---

## 1. Executive Summary & Core Mission

### The Business Reality
Small and medium retail store owners (groceries, personal care, apparel, specialty retail) have two finite resources:
1. **Shelf Space** (every square foot must generate revenue).
2. **Working Capital** (cash trapped in unsold inventory prevents buying bestsellers).

### The "Closed-World" Trap (Why other software fails)
Traditional POS/ERP software (Square, Lightspeed, Vyapar, Marg) operates in a closed database:
- When a product like *Ex-Vessel Shampoo* (50 units in stock, only 4 sold in 60 days) sits idle, the software only says: *"Slow mover. Discount it by 20%."*
- It cannot tell the owner: *"What should I replace it with tomorrow morning that actually sells?"*

### The StorePulse Solution
StorePulse solves the complete cycle in **5 integrated modules**:
1. **Catalog & Inventory**: Product master + real-time stock ledger.
2. **POS & Billing**: Fast counter checkout + instant receipts + auto-stock deduction.
3. **Trapped Capital Watchdog**: Autonomous detection of frozen capital and low-velocity SKUs.
4. **Open-World AI Replacement Engine**: Live web market intelligence (Brave Search / Google) extracting real consumer ratings, trending formulations, and wholesale margin arbitrage to recommend the best replacement SKU.
5. **Two-Step Actionable Execution**:
   - *Step A (Liquidate Old)*: Auto-generates a POS bundle combo (e.g., pair failing shampoo with #1 conditioner at 15% off).
   - *Step B (Onboard New)*: One-click catalog swap with pre-filled purchase order specs.

---

## 2. System Architecture

```
                       ┌──────────────────────────────────────────┐
                       │           React 19 + Vite Frontend       │
                       │   (Dashboard, POS, Catalog, Inventory,   │
                       │          AI Replacement Hub)             │
                       └────────────────────┬─────────────────────┘
                                            │ HTTP / JSON
                                            ▼
                       ┌──────────────────────────────────────────┐
                       │          Flask REST API Backend          │
                       │               (Port 5000)                │
                       ├────────────────────┬─────────────────────┤
                       │  Operational Core  │   AI Decision Engine│
                       │  - Products API    │   - Watchdog Trigger│
                       │  - Inventory API   │   - Web Sourcing    │
                       │  - POS Billing API │   - Value Scoring   │
                       │  - Analytics API   │   - Bundle Recipe   │
                       └─────────┬──────────┴──────────┬──────────┘
                                 │                     │
                                 ▼                     ▼
                     ┌──────────────────────┐   ┌─────────────────┐
                     │ SQLite Store DB      │   │ External Web    │
                     │ (data/storepulse.db) │   │ Market Search   │
                     │ - products           │   │ (Brave API)     │
                     │ - inventory_txs      │   └─────────────────┘
                     │ - sales & sale_items │
                     │ - ai_recommendations │
                     └──────────────────────┘
```

### Technology Stack
- **Backend**: Python 3.11+, Flask, SQLAlchemy ORM, SQLite3.
- **Frontend**: React 19, Vite, Recharts, Lucide React, Axios.
- **AI / Sourcing**: Brave Search API (stdlib HTTP client in `src/pipeline/recommendations/web_alternatives.py`), heuristic value-quality-margin scoring.
- **Environment**: Single store instance, zero external DB configuration required.

---

## 3. Database Schema (SQLite + SQLAlchemy)

### 3.1 Table: `products`
The master catalog for all SKUs in the store.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique product ID |
| `sku` | VARCHAR(64) | UNIQUE, NOT NULL, INDEXED | Stock Keeping Unit (e.g. `HERO-101`) |
| `barcode` | VARCHAR(64) | INDEXED, NULLABLE | Barcode for POS scanner |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `description` | TEXT | NULLABLE | Detailed specs/ingredients |
| `category` | VARCHAR(100) | NOT NULL, INDEXED | Top-level category (e.g., `Personal Care`) |
| `subcategory` | VARCHAR(100) | INDEXED, NULLABLE | Subcategory (e.g., `Hair Care`) |
| `brand` | VARCHAR(100) | NULLABLE | Brand name |
| `supplier` | VARCHAR(100) | NULLABLE | Primary vendor/distributor |
| `cost_price` | FLOAT | NOT NULL, DEFAULT 0.0 | Wholesale purchase cost per unit |
| `selling_price` | FLOAT | NOT NULL, DEFAULT 0.0 | Retail selling price per unit |
| `stock_quantity` | INTEGER | NOT NULL, DEFAULT 0 | Current units on shelf/backroom |
| `min_stock_alert` | INTEGER | NOT NULL, DEFAULT 10 | Low stock threshold trigger |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'active' | `active`, `clearance`, `discontinued` |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTC | Creation timestamp |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTC | Last modified timestamp |

**Computed Properties**:
- $\text{Profit Margin (\%)} = \frac{\text{selling\_price} - \text{cost\_price}}{\text{selling\_price}} \times 100$
- $\text{Trapped Capital (\$ / ₹)} = \text{stock\_quantity} \times \text{cost\_price}$

---

### 3.2 Table: `inventory_transactions`
The immutable audit trail for every single stock change.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Transaction ID |
| `product_id` | INTEGER | FOREIGN KEY (`products.id`), INDEXED | Target product |
| `transaction_type` | VARCHAR(30) | NOT NULL | `restock`, `sale`, `adjustment`, `writeoff`, `return` |
| `quantity` | INTEGER | NOT NULL | Signed delta (+ for addition, - for deduction) |
| `balance_after` | INTEGER | NOT NULL | Stock level immediately after event |
| `unit_cost` | FLOAT | NOT NULL, DEFAULT 0.0 | Unit cost at time of transaction |
| `reference_id` | VARCHAR(64) | NULLABLE | Receipt #, PO #, or invoice # |
| `notes` | VARCHAR(255) | NULLABLE | Contextual reason |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTC | Timestamp |

---

### 3.3 Table: `sales`
The header for every counter billing checkout.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Internal sale ID |
| `receipt_no` | VARCHAR(64) | UNIQUE, NOT NULL, INDEXED | Human-readable bill ID (e.g. `REC-202611-001`) |
| `subtotal` | FLOAT | NOT NULL, DEFAULT 0.0 | Total before tax and discounts |
| `tax_amount` | FLOAT | NOT NULL, DEFAULT 0.0 | Tax charged (e.g. GST) |
| `discount_amount` | FLOAT | NOT NULL, DEFAULT 0.0 | Promo/bundle discount deducted |
| `total_amount` | FLOAT | NOT NULL, DEFAULT 0.0 | Final amount paid by customer |
| `payment_method` | VARCHAR(30) | NOT NULL, DEFAULT 'cash' | `cash`, `card`, `upi`, `split` |
| `customer_name` | VARCHAR(100) | NULLABLE | Customer name (optional) |
| `customer_phone` | VARCHAR(20) | NULLABLE | For digital receipt SMS/WhatsApp |
| `notes` | TEXT | NULLABLE | Staff notes |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTC | Timestamp of checkout |

---

### 3.4 Table: `sale_items`
Individual line items inside each sale.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Line item ID |
| `sale_id` | INTEGER | FOREIGN KEY (`sales.id`), INDEXED | Parent sale |
| `product_id` | INTEGER | FOREIGN KEY (`products.id`), INDEXED | Product sold |
| `quantity` | INTEGER | NOT NULL, DEFAULT 1 | Units sold |
| `unit_price` | FLOAT | NOT NULL | Price charged per unit |
| `unit_cost` | FLOAT | NOT NULL | Cost price at time of sale (for margin tracking) |
| `discount` | FLOAT | NOT NULL, DEFAULT 0.0 | Line item discount |
| `total_price` | FLOAT | NOT NULL | `(quantity * unit_price) - discount` |
| `is_bundle` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether sold as part of an AI clearance bundle |

---

### 3.5 Table: `ai_recommendations`
Stores AI-generated market substitutes for underperforming products.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Recommendation ID |
| `product_id` | INTEGER | FOREIGN KEY (`products.id`), INDEXED | Flagged failing product |
| `recommended_title` | VARCHAR(255) | NOT NULL | Name of proposed substitute |
| `recommended_brand` | VARCHAR(100) | NULLABLE | Brand of proposed substitute |
| `recommended_price` | FLOAT | NULLABLE | Market retail price |
| `recommended_rating` | FLOAT | NULLABLE | Online consumer rating (e.g., `4.6`) |
| `review_count` | INTEGER | DEFAULT 0 | Volume of online reviews verified |
| `value_quality_score` | FLOAT | DEFAULT 0.0 | Normalized match score ($0.0 \to 1.0$) |
| `reasoning` | TEXT | NULLABLE | Plain-language explanation for the store owner |
| `source_url` | VARCHAR(500) | NULLABLE | Verification link for pricing/reviews |
| `bundle_suggestion` | TEXT | NULLABLE | POS recipe to liquidate the existing old stock |
| `status` | VARCHAR(30) | NOT NULL, DEFAULT 'pending' | `pending`, `accepted`, `dismissed` |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTC | Timestamp |

---

### 3.6 Table: `store_settings`
Singleton table (one row) holding store-wide configuration.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, DEFAULT 1 | Always 1 (singleton) |
| `store_name` | VARCHAR(255) | NOT NULL | Display name on receipts, dashboard |
| `owner_name` | VARCHAR(100) | NULLABLE | Owner's name for personalized copy |
| `store_address` | TEXT | NULLABLE | Full address for receipts |
| `store_phone` | VARCHAR(20) | NULLABLE | Contact phone on receipts |
| `store_email` | VARCHAR(100) | NULLABLE | Contact email |
| `gstin` | VARCHAR(20) | NULLABLE | GSTIN for tax invoices |
| `tax_rate_default` | FLOAT | DEFAULT 0.05 | Default tax rate (e.g., 0.05 = 5%) |
| `currency_symbol` | VARCHAR(10) | DEFAULT '₹' | Currency symbol for display |
| `timezone` | VARCHAR(50) | DEFAULT 'Asia/Kolkata' | IANA timezone |
| `receipt_footer_text` | TEXT | NULLABLE | Custom footer on printed receipts |
| `setup_completed` | BOOLEAN | DEFAULT FALSE | Has onboarding been completed? |
| `setup_completed_at` | DATETIME | NULLABLE | Timestamp when setup finished |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTC | Creation timestamp |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTC | Last modified timestamp |

---

### 3.7 Table: `suppliers`
Your suppliers/distributors — one per brand or one for everything.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Supplier ID |
| `name` | VARCHAR(255) | NOT NULL | e.g., "Unilever Distribution" |
| `contact_person` | VARCHAR(100) | NULLABLE | Sales rep name |
| `phone` | VARCHAR(20) | NULLABLE | Primary phone |
| `whatsapp` | VARCHAR(20) | NULLABLE | WhatsApp number (can differ from phone) |
| `email` | VARCHAR(100) | NULLABLE | Order email |
| `preferred_channel` | VARCHAR(20) | DEFAULT 'whatsapp' | `whatsapp`, `email`, `phone`, `call` |
| `notes` | TEXT | NULLABLE | Terms, min order, delivery days |
| `payment_terms` | VARCHAR(100) | NULLABLE | e.g., "Net 30", "COD" |
| `min_order_value` | FLOAT | DEFAULT 0.0 | Minimum order amount |
| `delivery_schedule` | VARCHAR(100) | NULLABLE | e.g., "Tue/Fri", "Daily 10 AM" |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft delete |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTC | |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTC | |

---

### 3.8 Table: `message_templates`
Pre-written messages per channel — global or per-supplier.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | |
| `channel` | VARCHAR(20) | NOT NULL | `whatsapp`, `email`, `sms`, `call` |
| `supplier_id` | INTEGER | FK (`suppliers.id`), NULLABLE | NULL = global template |
| `template_text` | TEXT | NOT NULL | With placeholders: `{{product_name}}`, `{{sku}}`, `{{qty}}`, `{{store_name}}`, `{{supplier_name}}`, `{{contact_person}}` |
| `subject_line` | VARCHAR(255) | NULLABLE | For email channel |
| `is_default` | BOOLEAN | DEFAULT FALSE | One default per channel |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTC | |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTC | |

---

### 3.9 Table: `purchase_orders`
Tracks restock orders sent to suppliers.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | PO ID |
| `supplier_id` | INTEGER | FK (`suppliers.id`), NOT NULL, INDEXED | |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'drafted' | `drafted`, `sent`, `confirmed`, `received`, `cancelled` |
| `items_json` | TEXT | NOT NULL | JSON array: `[{"product_id": 1, "qty": 30, "unit_cost": 210}]` |
| `total_amount` | FLOAT | DEFAULT 0.0 | Sum of qty × unit_cost |
| `sent_via_channel` | VARCHAR(20) | NULLABLE | `whatsapp`, `email`, `phone`, `call` |
| `sent_at` | DATETIME | NULLABLE | When order was sent |
| `confirmed_at` | DATETIME | NULLABLE | Supplier confirmed |
| `received_at` | DATETIME | NULLABLE | Stock physically received |
| `notes` | TEXT | NULLABLE | Internal notes |
| `created_at` | DATETIME | NOT NULL, DEFAULT UTC | |
| `updated_at` | DATETIME | NOT NULL, DEFAULT UTC | |

---

### 3.10 Updated: `products` table — add supplier link
Add to `products` table:
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `supplier_id` | INTEGER | FK (`suppliers.id`), NULLABLE, INDEXED | Which supplier provides this |
| `reorder_qty_suggestion` | INTEGER | DEFAULT 0 | Suggested order qty (auto-calc from velocity) |

## 4. API Specifications (REST Contract)

All endpoints accept and return `application/json`. Base URL: `http://localhost:5000`.

### 4.1 Products API
- `GET /api/products`:
  - **Query Params**: `search` (string), `category` (string), `status` (string), `sort_by` (`name`, `price`, `stock`, `trapped_capital`), `order` (`asc`, `desc`).
  - **Response (200)**: `{"products": [...], "total": 12, "categories": ["Grocery", "Household", ...]}`
- `POST /api/products`:
  - **Payload**: `{"name": "...", "sku": "...", "category": "...", "cost_price": 200, "selling_price": 280, "stock_quantity": 40}`
  - **Response (201)**: Created product object. Logs initial `InventoryTransaction`.
- `GET /api/products/<id>`: Returns single product detail.
- `PUT /api/products/<id>`: Updates product attributes.
- `DELETE /api/products/<id>`: Deletes SKU (or sets status to discontinued).

### 4.2 Inventory API
- `GET /api/inventory`:
  - **Response (200)**:
    ```json
    {
      "items": [
        {
          "id": 1,
          "name": "Ex-Vessel Shampoo",
          "stock_quantity": 46,
          "trapped_capital": 14720.0,
          "is_low_stock": false,
          "is_out_of_stock": false
        }
      ],
      "kpis": {
        "total_skus": 12,
        "total_units": 415,
        "total_valuation": 84520.0,
        "low_stock_count": 2,
        "out_of_stock_count": 0
      }
    }
    ```
- `POST /api/inventory/restock`:
  - **Payload**: `{"product_id": 1, "quantity": 25, "unit_cost": 210.0, "reference_id": "PO-991", "notes": "Weekly restock"}`
  - **Effect**: Increases `product.stock_quantity`, records `restock` transaction.
- `POST /api/inventory/adjust`:
  - **Payload**: `{"product_id": 1, "new_quantity": 42, "reason": "Damaged bottle discarded", "type": "writeoff"}`
  - **Effect**: Sets new stock, records adjustment delta.
- `GET /api/inventory/transactions`: Returns paginated audit log of stock movements.

### 4.3 Sales & Billing (POS) API
- `POST /api/sales`:
  - **Payload**:
    ```json
    {
      "items": [
        {"product_id": 1, "quantity": 2, "unit_price": 299.0, "discount": 0.0, "is_bundle": false},
        {"product_id": 3, "quantity": 1, "unit_price": 125.0, "discount": 10.0, "is_bundle": true}
      ],
      "payment_method": "upi",
      "customer_name": "Rohan",
      "customer_phone": "9876543210",
      "notes": "Counter sale"
    }
    ```
  - **Server Execution**:
    1. Validates stock availability for each item.
    2. Deducts `product.stock_quantity` atomically.
    3. Records negative delta in `inventory_transactions`.
    4. Generates unique `receipt_no` (`REC-YYYYMM-XXXX`).
    5. Saves `Sale` + `SaleItem` rows.
  - **Response (201)**: Complete receipt with subtotal, tax, discount, and total.
- `GET /api/sales`: Returns sales history with optional date range filters (`start_date`, `end_date`).
- `GET /api/sales/<id>`: Returns full itemized receipt breakdown.

### 4.4 AI Underperformance & Replacement API
- `GET /api/replacements/underperforming`:
  - **Engine Logic**: Computes 30-day velocity ratio for each product:
    $$\text{Velocity} = \frac{\text{Units Sold in 30 Days}}{\text{Average Stock on Hand}}$$
    A product is flagged if:
    $$\text{Velocity} < 0.20 \quad \text{AND} \quad \text{Trapped Capital} > \$50\text{ (or }₹3,000\text{)} \quad \text{AND} \quad \text{Days on Shelf} \ge 30$$
  - **Response (200)**: List of flagged products with units unsold, trapped capital, and days stagnant.
- `POST /api/replacements/search`:
  - **Payload**: `{"product_id": 6, "limit": 3}`
  - **Engine Logic**: Executes `ProductAlternativeResearcher` using Brave Search API:
    1. Queries live web for top competitors in the same subcategory and price bracket.
    2. Scrapes ratings, review volumes, prices, and ingredient highlights.
    3. Calculates `value_quality_score`.
    4. Auto-generates POS bundle recipe to liquidate existing stock.
    5. Caches recommendations in `ai_recommendations` table.
  - **Response (200)**: List of recommended replacements with rationale and bundle recipe.
- `POST /api/replacements/accept`:
  - **Payload**: `{"recommendation_id": 1, "action": "replace_sku", "apply_bundle": true}`
  - **Effect**: Updates recommendation status to `accepted`, flags old product as `clearance`, and stages the new product in catalog.
- `POST /api/replacements/dismiss`:
  - **Payload**: `{"recommendation_id": 1, "snooze_days": 30}`

### 4.5 Analytics API
- `GET /api/analytics/summary`:
  - **Response (200)**:
    - `revenue_overview`: Day/Week/Month totals.
    - `profit_margins`: Overall store margin + per-category margins.
    - `capital_health`: Total inventory capital vs. Trapped dead-stock capital.
    - `top_sellers`: Top 5 SKUs by volume and revenue.
    - `dead_stock`: Bottom 5 SKUs with highest trapped capital and zero movement.

---

### 4.6 Setup & Onboarding API
- `GET /api/setup/status`:
  - **Response (200)**: `{ "setup_completed": true, "current_step": 5, "store_name": "My Store" }`
- `POST /api/setup/store`:
  - **Payload**: `{ "store_name": "Krishna General Store", "owner_name": "Rajesh Kumar", "store_address": "123 Main St", "store_phone": "9876543210", "store_email": "rajesh@store.com", "gstin": "27ABCDE1234F1Z5", "tax_rate_default": 0.05, "currency_symbol": "₹", "timezone": "Asia/Kolkata", "receipt_footer_text": "Thank you for shopping!" }`
  - **Response (201)**: Created/updated `StoreSettings` row.
- `POST /api/setup/suppliers`:
  - **Payload**: `{ "suppliers": [ { "name": "Unilever Distribution", "contact_person": "Rajesh", "phone": "9876543210", "whatsapp": "9876543210", "email": "orders@unilever.in", "preferred_channel": "whatsapp", "notes": "Min ₹5000, Tue/Fri delivery", "payment_terms": "Net 30", "min_order_value": 5000, "delivery_schedule": "Tue/Fri" } ] }`
  - **Response (201)**: Created suppliers, returns array with IDs.
- `POST /api/setup/templates`:
  - **Payload**: `{ "templates": [ { "channel": "whatsapp", "template_text": "Hi {{contact_person}}, need {{qty}} units of {{product_name}} ({{sku}}) for {{store_name}}. Please confirm delivery. Thanks!", "is_default": true }, { "channel": "email", "subject_line": "Restock Order - {{product_name}}", "template_text": "Dear {{supplier_name}},\n\nPlease supply:\n- {{product_name}} ({{sku}}): {{qty}} units\n\nTotal: {{total_amount}}\n\nThanks,\n{{store_name}}", "is_default": true } ] }`
  - **Response (201)**: Created message templates.
- `POST /api/setup/complete`:
  - **Effect**: Sets `setup_completed=true`, `setup_completed_at=now()`, seeds initial categories if empty.
  - **Response (200)**: `{ "success": true, "redirect": "/" }`

---

### 4.7 Supplier Management API (Post-Setup)
- `GET /api/suppliers`:
  - **Response (200)**: `{ "suppliers": [...], "total": 5 }`
- `POST /api/suppliers`:
  - **Payload**: `{ "name": "...", "contact_person": "...", "phone": "...", "whatsapp": "...", "email": "...", "preferred_channel": "whatsapp", "notes": "...", "payment_terms": "Net 30", "min_order_value": 5000, "delivery_schedule": "Tue/Fri" }`
  - **Response (201)**: Created supplier.
- `PUT /api/suppliers/<id>`: Updates supplier.
- `DELETE /api/suppliers/<id>`: Soft delete (`is_active=false`).
- `GET /api/suppliers/<id>/templates`:
  - **Response (200)**: Message templates for this supplier (falls back to global).
- `POST /api/suppliers/<id>/templates`: Save per-supplier template override.

---

### 4.8 Low Stock & Restock Communication API
- `GET /api/inventory/low-stock`:
  - **Query**: `threshold` (optional, overrides product's `min_stock_alert`)
  - **Response (200)**: Products where `stock_quantity <= min_stock_alert`, each with supplier info, suggested reorder qty, estimated cost.
- `POST /api/inventory/generate-restock-message`:
  - **Payload**: `{ "product_id": 1, "supplier_id": 2, "channel": "whatsapp", "quantity": 30 }`
  - **Logic**: Loads template (supplier-specific → global), fills placeholders, returns `{ "message": "Hi Rajesh, need 30 units...", "url": "https://wa.me/919876543210?text=..." }`
  - **Channels**:
    - `whatsapp` → `wa.me` link with encoded text
    - `email` → `mailto:` link with subject + body
    - `phone` / `call` → `tel:` link
    - `sms` → `sms:` link
- `POST /api/purchase-orders`:
  - **Payload**: `{ "supplier_id": 2, "items": [{"product_id": 1, "qty": 30, "unit_cost": 210}], "sent_via_channel": "whatsapp" }`
  - **Effect**: Creates `PurchaseOrder` with status `sent`, logs `sent_at`.
- `POST /api/purchase-orders/<id>/receive`:
  - **Payload**: `{ "items": [{"product_id": 1, "received_qty": 30}] }`
  - **Effect**: Updates `PurchaseOrder` status → `received`, increases product stock, logs `restock` transactions.

---

### 4.9 Store Settings API
- `GET /api/settings/store`: Returns `StoreSettings` singleton.
- `PUT /api/settings/store`: Updates store settings (name, address, tax, receipt footer, etc.).

---

## 5. Frontend Architecture & Screen Specifications

All screens reside under `frontend/src/pages/` and fit inside the existing `Layout.jsx` with dark-theme styling.

### 5.1 Navigation Structure (`TopBar.jsx` & Router)
| Route | Label | Icon | Purpose |
| :--- | :--- | :--- | :--- |
| `/` | **Dashboard** | `BarChart2` | Real-time sales, trapped capital KPI, alerts |
| `/pos` | **POS & Billing** | `ShoppingCart` | Fast checkout, barcode/product search, receipt |
| `/catalog` | **Products** | `Package` | Add, edit, filter, delete catalog SKUs |
| `/inventory` | **Inventory** | `Boxes` | Stock levels, Restock modal, low-stock warnings |
| `/replacements` | **AI Replacement** | `Sparkles` | Underperforming SKU radar, live web alternatives |
| `/analytics` | **Analytics** | `TrendingUp` | Revenue & profit margins, category contribution |
| `/setup` | **Setup Wizard** | `Settings` | First-time onboarding (guarded, full-screen) |

---

### 5.2 Screen Specification 0: First-Time Setup Wizard (`/setup`) — **Full-Screen, No Chrome**

**Route Guard**: If `GET /api/setup/status` returns `setup_completed: false`, **all routes redirect to `/setup`** (except `/health`).

**Visual Identity**:
- **Living gradient background** — slow, mesmerizing color shifts (CSS `@keyframes` + `background-size: 400%`). Colors: warm coral → soft teal → deep indigo → warm amber. Never distracting, always calm.
- **No sidebar, no topbar, no footer** — pure focus. Centered card with subtle glassmorphism (`backdrop-filter: blur(20px)`).
- **Micro-animations everywhere** — `framer-motion` for: step transitions (slide + fade), input focus (label lifts, border glows), button press (scale 0.98), card entrance (staggered 100ms), progress bar fill.
- **Typography**: Large, friendly headings (`clamp(2rem, 5vw, 3rem)`), generous line-height, warm gray text (not black).
- **Illustrations**: Subtle SVG line art per step (store front → delivery truck → bell icon → speech bubble → celebration burst).

**Step Indicator** (top of card):
- 5 pills: `1. Your Store` → `2. Suppliers` → `3. Alerts` → `4. Messages` → `5. Ready`
- Current: filled + pulse animation. Completed: checkmark. Pending: subtle outline.

---

#### **Step 1: "Let's get to know your store"**
**Copy**: *"Tell us about your shop. This shows up on receipts, your dashboard, and when you message suppliers."*

| Field | Type | Validation | Helper Text |
|-------|------|------------|-------------|
| Store Name | Text | Required, 2–100 chars | "Appears on receipts & dashboard" |
| Owner Name | Text | Optional | "We'll use this to personalize messages" |
| Address | Textarea | Optional | "Full address for receipts" |
| Phone | Tel | Optional, Indian format | "On receipts & WhatsApp link" |
| Email | Email | Optional | "For email orders & reports" |
| GSTIN | Text | Optional, 15-char pattern | "For tax invoices (GST)" |
| Default Tax % | Number | 0–100, default 5 | "Applied to new sales automatically" |
| Currency | Select | ₹, $, €, £ | "Display currency" |
| Receipt Footer | Textarea | Optional | "Thank you note at bottom of bills" |

**Buttons**: `[Back]` (disabled) — `[Continue →]` (primary, loading state on submit)

**Animation**: Card slides in from right. Inputs stagger-fade in (50ms each). Focus: label floats up, border glows `var(--accent)`.

---

#### **Step 2: "Where do you get your stock?"**
**Copy**: *"Add your suppliers — one per brand, or one distributor for everything. We'll use this to draft restock messages for you."*

**UI**:
- **Empty state**: Illustrated card: *"No suppliers yet. Add your first one below."*
- **Add Supplier Form** (inline, expands smoothly):
  - Supplier Name* (text)
  - Contact Person (text) — *"Your sales rep's name"*
  - Phone (tel) — *"For calls"*
  - WhatsApp (tel) — *"Can be different from phone"*
  - Email (email) — *"For email orders"*
  - **Preferred Channel** — 4 chips: 📱 WhatsApp | 📧 Email | 📞 Call | 📲 SMS (radio group, visual selection)
  - Notes (textarea) — *"Min order, delivery days, payment terms"*
  - Payment Terms (select: Net 15, Net 30, COD, Custom)
  - Min Order Value (number)
  - Delivery Schedule (text) — *"e.g., Tue/Fri, Daily 10 AM"*
- **Supplier List** (below form): Cards with name, contact person, preferred channel badge, edit/delete icons.
- **Drag to reorder** (optional, nice-to-have).

**Buttons**: `[Back]` — `[Continue →]`

**Animation**: Form slides down from "Add Supplier" button. List items stagger in. Channel chips have press ripple.

---

#### **Step 3: "When should we nudge you about low stock?"**
**Copy**: *"Set a default alert level. You can fine-tune per product later."*

**UI**:
- **Global Threshold**: Large number input with `+`/`-` steppers: *"Alert me when any product drops to **15** units or below"*
- **Visual preview**: Mini product cards showing:
  - ✅ Dove Shampoo (42 in stock) — *Safe*
  - 🔴 Ex-Vessel Shampoo (12 in stock) — *Low!* (if threshold 15)
- **Per-Category Override** (collapsible): *"Different thresholds for different categories?"* → expand → list of categories with individual number inputs.

**Buttons**: `[Back]` — `[Continue →]`

---

#### **Step 4: "How do you talk to suppliers?"**
**Copy**: *"Write your message once. We'll fill in the details (product, quantity, your store name) every time."*

**UI**:
- **Channel Tabs**: WhatsApp | Email | Call Script | SMS
- **Per Channel**:
  - **Subject Line** (email only)
  - **Template Editor** — textarea with **placeholder chips** below:
    - `{{product_name}}` `{{sku}}` `{{qty}}` `{{unit_cost}}` `{{total_amount}}`
    - `{{store_name}}` `{{owner_name}}` `{{store_phone}}` `{{store_email}}`
    - `{{supplier_name}}` `{{contact_person}}` `{{delivery_schedule}}`
  - Click chip → inserts at cursor.
  - **Live Preview Pane** (right side, updates real-time): Shows rendered message with sample data.
- **Default Template** toggle: *"Use this for all suppliers unless overridden."*

**Buttons**: `[Back]` — `[Continue →]`

---

#### **Step 5: "You're ready! 🎉"**
**Copy**: *"**{{store_name}}** is set up with **{{supplier_count}}** supplier(s). Your low-stock threshold is **{{threshold}}** units."*

**Animation**:
- Gradient background bursts (radial gradient expansion)
- Confetti burst (canvas-based, lightweight)
- Summary card scales in with spring physics

**Summary Card**:
- Store name, owner name
- Supplier count + names (chips)
- Default tax, currency
- Low stock threshold
- Channels configured

**Buttons**:
- `[Take me to my Dashboard →]` (large, primary, navigates to `/`, calls `POST /api/setup/complete`)
- `[Edit Suppliers]` (secondary, goes back to Step 2)
- `[Skip for now]` (ghost, small, sets minimal defaults, completes setup)

---

#### **Accessibility & Polish**
- **Keyboard navigable**: Tab through all inputs, Enter on buttons, Escape to go back
- **Screen reader**: `aria-live` announcements for step changes, errors
- **Reduced motion**: `prefers-reduced-motion` disables gradient shift, confetti
- **Responsive**: Works on 320px mobile → 1440px desktop (card max-width 520px)
- **Offline-friendly**: No external fonts (system UI stack), no heavy libs

---

### 5.3 Screen Specification 1: POS Billing (`/pos`)
- **Layout**: Two-column layout (65% Product Selection / Scanner, 35% Active Cart).
- **Left Panel (Product Selector)**:
  - Sticky barcode/name search bar (`Auto-focus` on load).
  - Quick Category filter chips (All, Personal Care, Grocery, Snacks, etc.).
  - Product Grid Cards: Displays product name, stock badge, selling price, and single-click "Add to Cart" button.
- **Right Panel (Cart & Checkout)**:
  - Line items list: Product title, quantity stepper (`+` / `-`), unit price, line subtotal, delete button.
  - Clearance Bundle Pill: If a product has an active AI bundle (e.g. 15% off combo), displays a highlighted tag: *"AI Bundle Applied: -$30"*.
  - Billing Breakdown: Subtotal, Tax (e.g., 5% GST toggle), Total.
  - Payment Method Selector: Cash, Card, UPI buttons.
  - Action Button: Large green **"Complete Sale & Print Bill"** button.
  - Modal: Instant printable / downloadable receipt on completion.

---

### 5.3 Screen Specification 2: Products Catalog (`/catalog`)
- **Header**: "Add New Product" modal trigger button + search input + category dropdown.
- **Table Columns**: SKU, Barcode, Product Name, Category, Cost Price, Selling Price, Margin %, Stock On Hand, Status Tag, Actions (Edit/Delete).
- **Add/Edit Modal**: Clean form with fields: Name, Category, Subcategory, Brand, Cost, Price, Stock, Alert Threshold.

---

### 5.4 Screen Specification 3: Inventory Management (`/inventory`)
- **Top KPI Cards**:
  1. *Total Inventory Valuation* ($ / ₹).
  2. *Total Units on Hand*.
  3. *Trapped Capital (At-Risk)* (Highlighted in amber).
  4. *Low Stock Alerts* (Count of SKUs needing reorder).
- **Restock Modal**: Select product, enter supplier invoice/PO #, enter quantity added, enter cost price.
- **Stock Audit Modal**: Quick-adjust stock with reasons (write-off, count mismatch, return).
- **Stock Movement Log**: Filterable audit trail of every transaction.

---

### 5.5 Screen Specification 4: AI Replacement Hub (`/replacements`)
- **Top Banner**: *"Trapped Capital Radar: $X locked in stagnant products"*.
- **Left Column: Underperforming Products Queue**:
  - Cards for products with velocity < 20%.
  - Highlights: Days stagnant (e.g., 60 days), Units unsold (e.g., 46 of 50), Trapped Cash ($14,720).
  - Button: **"Find Market Replacements"** (triggers live AI search).
- **Right Column: AI Recommendation Dossier**:
  - Displays top 3 live-scraped alternative brands.
  - Each recommendation card includes:
    - *Title & Brand*.
    - *Price comparison* (e.g., $279 vs current $490 -> 43% cheaper for customer).
    - *Customer proof* (4.6★ across 18,000+ reviews).
    - *Margin improvement* (32% margin vs current 24%).
    - *Plain English Rationale* ("Why this replaces Ex-Vessel successfully").
    - *POS Clearance Recipe* (e.g., "Bundle remaining 46 Ex-Vessel bottles with Dove Conditioner at 20% off").
  - Action Buttons:
    - **"Accept & Replace SKU"** (auto-stages new SKU, marks old SKU for clearance bundle).
    - **"Dismiss / Snooze"**.

---

### 5.6 Screen Specification 5: Analytics & Reports (`/analytics`)
- **Revenue & Profit Bar Chart**: Period toggle (Week: 7 daily bars; Month: 4 weekly bars; Quarter: 3 monthly bars).
- **Revenue by Division / Category Pie Chart**: Complete solid circle (0 inner radius, bottom legend).
- **Product Velocity Ranking**: Top 5 bestsellers vs. Top 5 dead-stock money drains.

---

## 6. Implementation Phases & Step-by-Step Checklist

Any coding agent should execute these phases sequentially. Do not move to the next phase until the verification test passes.

### Phase 0: First-Time Setup & Onboarding Wizard (The "Welcome Experience")
**Goal**: A beautiful, animated, guided setup that feels like a helpful assistant — not a form. Covers all store personalization before the user sees any dashboard.

#### 0.1 Backend: Setup State & Store Settings Models
- [ ] Add `StoreSettings` model in `src/storepulse/models.py`:
  - `store_name`, `store_address`, `store_phone`, `store_email`, `gstin`, `tax_rate_default`
  - `currency_symbol`, `timezone`, `receipt_footer_text`
  - `setup_completed` (boolean), `setup_completed_at` (datetime)
- [ ] Add `Supplier` model in `src/storepulse/models.py`:
  - `name`, `contact_person`, `phone`, `whatsapp`, `email`
  - `preferred_channel` (enum: `whatsapp`, `email`, `phone`, `call`)
  - `notes`, `payment_terms`, `min_order_value`, `delivery_schedule`
  - `is_active` (boolean)
- [ ] Add `MessageTemplate` model in `src/storepulse/models.py`:
  - `channel` (whatsapp/email/sms/call), `template_text` with placeholders
  - `supplier_id` (nullable — global or per-supplier)
  - `is_default` (boolean)
- [ ] Add `PurchaseOrder` model in `src/storepulse/models.py`:
  - `supplier_id`, `status` (drafted/sent/confirmed/received/cancelled)
  - `items` (JSON: product_id, qty, unit_cost), `total_amount`
  - `sent_via_channel`, `sent_at`, `confirmed_at`, `received_at`
  - `notes`
- [ ] Update `Product` model: add `supplier_id` (FK to Supplier), `reorder_qty_suggestion`
- [ ] Create `src/storepulse/routes/setup.py` with endpoints:
  - `GET /api/setup/status` → returns `{ setup_completed: bool, current_step: int }`
  - `POST /api/setup/store` → store basic info (name, address, phone, email, GST, tax)
  - `POST /api/setup/suppliers` → bulk create suppliers with contact channels
  - `POST /api/setup/templates` → save message templates per channel
  - `POST /api/setup/complete` → marks `setup_completed=true`, seeds initial data
- [ ] Register `setup_bp` in `serve.py` under `/api/setup/*`

#### 0.2 Frontend: Onboarding Wizard (`/setup` route, full-screen, guarded)
- [ ] Create `frontend/src/pages/SetupWizard.jsx` — **full-screen, no sidebar/topbar**
- [ ] **Animated gradient background** — living gradient that shifts gently (CSS keyframes + `framer-motion` or pure CSS)
- [ ] **Step indicator** — top progress bar: `1. Your Store → 2. Suppliers → 3. Alerts → 4. Messages → 5. Ready`
- [ ] **Step 1: Your Store** — warm welcome copy, animated inputs:
  - Store name, owner name, address, phone, email, GSTIN, default tax %
  - Micro-animations on focus, helpful hints ("This appears on receipts")
  - "Continue" button with loading state → saves via `/api/setup/store`
- [ ] **Step 2: Your Suppliers** — "Where do you get your stock?"
  - Add multiple suppliers: name, contact person, phone, WhatsApp, email
  - **Channel chips** per supplier: 📱 WhatsApp | 📧 Email | 📞 Call (pick preferred)
  - "Add another supplier" → smooth list animation
  - Saves via `/api/setup/suppliers`
- [ ] **Step 3: Low Stock Alerts** — "When should we nudge you?"
  - Global default threshold (e.g., "Alert me when stock ≤ 15")
  - Per-category override option (expandable)
  - Preview: "Dove Shampoo at 12 units → 🔴 Low"
- [ ] **Step 4: Message Templates** — "How do you talk to suppliers?"
  - Per-channel editor: WhatsApp, Email, Call script
  - Placeholder chips: `{{product_name}}`, `{{sku}}`, `{{qty}}`, `{{store_name}}`, `{{supplier_name}}`
  - Live preview pane updates as you type
  - Saves via `/api/setup/templates`
- [ ] **Step 5: You're Ready!** — celebration animation (confetti/gradient burst)
  - Summary card: "Your store **'Krishna General Store'** is set up with 3 suppliers"
  - "Take me to my Dashboard" → navigates to `/`, sets `setup_completed=true`
- [ ] **Guard**: `App.jsx` checks `/api/setup/status` on load → redirects to `/setup` if not completed
- [ ] **Skip option** (small, subtle): "I'll do this later" → marks minimal defaults, goes to Dashboard

#### 0.3 Verification
- [ ] Fresh DB → visit `http://localhost:3000` → redirects to `/setup` → complete all steps → lands on Dashboard
- [ ] `GET /api/setup/status` returns `{ setup_completed: true }` after completion
- [ ] All entered data persists in DB (StoreSettings, Suppliers, MessageTemplates)
- [ ] Animations run at 60fps, no layout shift, accessible (keyboard nav, screen reader labels)

---

### Phase 1: Database Foundation & Product Master
- [ ] Initialize SQLite database at `data/storepulse.db`.
- [ ] Implement SQLAlchemy models in `src/storepulse/models.py` (`Product`, `InventoryTransaction`, `Sale`, `SaleItem`, `AIRecommendation`).
- [ ] Implement `src/storepulse/database.py` with scoped session and connection handling.
- [ ] Create `src/storepulse/seed.py` with 12+ realistic products (including the hero products, dead stock shampoo, and low-stock items).
- [ ] Run seed script and verify database integrity.
- **Verification**: `python -c "from storepulse.models import Product; print(Product.query.count())"` returns $>0$.

---

### Phase 2: REST API Endpoints
- [ ] Create `src/storepulse/routes/products.py` with full CRUD.
- [ ] Create `src/storepulse/routes/inventory.py` with `/restock`, `/adjust`, and `/transactions`.
- [ ] Create `src/storepulse/routes/sales.py` with atomic stock deduction and receipt generation.
- [ ] Create `src/storepulse/routes/replacements.py` with underperformance detection.
- [ ] Create `src/storepulse/routes/analytics.py` with summary KPIs.
- [ ] Register all Blueprints into Flask `serve.py` under `/api/*` with CORS enabled.
- **Verification**: Run `curl http://localhost:5000/api/products` and `curl http://localhost:5000/api/inventory`. Both return HTTP 200 with valid JSON.

---

### Phase 3: AI Market Search & Scoring Engine
- [ ] Wire `src/pipeline/recommendations/web_alternatives.py` to the `/api/replacements/search` route.
- [ ] Implement fallback heuristic sourcing for environments without an active Brave API key so the UI remains fully functional and realistic.
- [ ] Implement the POS bundle recipe generator:
  $$\text{Bundle Discount} = \max\left(10\%, \min\left(25\%, \frac{\text{Trapped Margin}}{2}\right)\right)$$
- [ ] Implement `/api/replacements/accept` to transition the failing SKU to `clearance` and register the replacement.
- **Verification**: POST to `/api/replacements/search` with `product_id=6` (Ex-Vessel Shampoo) returns 3 scored alternatives with ratings and bundle suggestions.

---

### Phase 4: Frontend POS & Catalog Screens
- [ ] Update `frontend/src/services/api.js` to connect to all `/api/*` endpoints (including `/api/setup/*`, `/api/suppliers/*`, `/api/inventory/low-stock`, `/api/inventory/generate-restock-message`, `/api/purchase-orders`).
- [ ] Build `frontend/src/pages/SetupWizard.jsx` — **full-screen onboarding wizard** (Phase 0.2):
  - Living gradient background (CSS keyframes), glassmorphism card, `framer-motion` animations
  - Step indicator (5 steps), step transitions (slide + fade)
  - Step 1: Store info form with animated inputs, helper text
  - Step 2: Supplier management (add multiple, channel chips, inline form)
  - Step 3: Low stock threshold (global + per-category override, visual preview)
  - Step 4: Message templates per channel (placeholder chips, live preview pane)
  - Step 5: Celebration animation (confetti, summary card), "Take me to Dashboard"
  - Guard: `App.jsx` checks `/api/setup/status` → redirects to `/setup` if not completed
  - Skip option, keyboard nav, reduced motion, responsive
- [ ] Build `frontend/src/pages/POS.jsx` (Product search + live cart + checkout + receipt modal).
- [ ] Update `frontend/src/pages/ProductCatalog.jsx` to read real products from `/api/products` and support Add/Edit/Delete.
- [ ] Build `frontend/src/pages/Inventory.jsx` (Stock counts, Restock modal, Low-stock alerts with "Order Now" buttons).
- [ ] Build `frontend/src/components/LowStockPopup.jsx` — reusable popup component:
  - Shows product name, current stock, supplier, suggested reorder qty
  - Channel buttons: 📱 WhatsApp | 📧 Email | 📞 Call (opens `wa.me:`, `mailto:`, `tel:` links)
  - "Edit Message" → opens template preview → send
  - "Mark as Ordered" → creates PurchaseOrder
  - "Remind me tomorrow" / "Dismiss"
- [ ] Update `frontend/src/components/TopBar.jsx` with links to `/`, `/pos`, `/catalog`, `/inventory`, `/replacements`, `/analytics`, `/setup`.
- [ ] Update `frontend/src/components/Sidebar.jsx` with Setup Wizard link (shown only if not completed).
- **Verification**: Fresh DB → visit `http://localhost:3000` → redirected to `/setup` → complete all 5 steps → lands on Dashboard with all data persisted.

---

### Phase 5: Frontend AI Replacement & Analytics Hub
- [ ] Build `frontend/src/pages/AIReplacements.jsx` (Stagnant products queue + AI Dossier cards + One-click Accept button).
- [ ] Update `frontend/src/pages/Dashboard.jsx` and `frontend/src/pages/Analytics.jsx` to pull real metrics from `/api/analytics/summary`.
- [ ] Verify that accepting an AI recommendation immediately reflects on the POS cart (as a clearance bundle) and on the catalog.
- **Verification**: Run `npm run build` and `npm run lint` in the `frontend` folder; 0 errors allowed.

---

## 7. Edge Cases & Safety Protocols

1. **Atomic Inventory Deduction**:
   - Stock deduction during a sale MUST be executed inside a database transaction. If stock is insufficient, the sale must abort with HTTP 400 (`"Insufficient stock for SKU X"`).
2. **Negative Stock Prevention**:
   - `stock_quantity` must never drop below 0. Restock and adjust endpoints must validate inputs strictly.
3. **Graceful Web Search Fallback**:
   - If the Brave Search API key is missing or encounters a rate limit, the engine must gracefully fall back to domain-knowledge retail alternatives without crashing the server.
4. **Idempotent Seeding**:
   - Running the seed script must clear and rebuild test data cleanly without leaving orphaned records.
5. **CORS & Dev Ports**:
   - CORS must continue to allow `http://localhost:*` and `http://127.0.0.1:*` to accommodate Vite dev server port switches.

---

## 8. Definition of Done (DoD)

The system is considered complete when:
1. **First-time setup**: Fresh DB → visit app → redirected to `/setup` → complete 5-step wizard (store info, suppliers, alerts, messages, ready) → lands on Dashboard with all data persisted.
2. A store owner can add a new product and restock it.
3. A cashier can scan/select the product in `/pos`, take cash/card/UPI, and print an itemized bill.
4. The inventory decreases accurately on every sale.
5. An underperforming product (like Ex-Vessel Shampoo) is flagged on `/replacements` with its trapped cash calculated.
6. Clicking "Find Market Replacements" delivers real alternatives with ratings, prices, and an automated clearance bundle recipe.
7. Accepting the replacement marks the dead stock for clearance at the POS and stages the new SKU.
8. **Low stock → Order Now**: Low stock popup appears → click WhatsApp/Email/Call → pre-filled message opens in your app → click Send → order tracked in PurchaseOrders.
9. All frontend builds (`npm run build`) and Python tests pass with 0 errors.
