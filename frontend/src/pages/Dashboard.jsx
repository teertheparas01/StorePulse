import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, ArrowDownRight, ArrowUpRight, BadgeIndianRupee, Boxes, Check, CircleDollarSign, ClipboardList, LoaderCircle, Package, Plus, Printer, RotateCcw, Search, Sparkles, X } from 'lucide-react';
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { createSale, getInventoryTransactions, getProducts, getSales, getUnderperformingProducts, searchReplacements } from '../services/api';
import './Dashboard.css';

const money = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value || 0));
const formatDate = (value) => new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

function getPeriodStart(period, now = new Date()) {
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  if (period === 'week') start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
  if (period === 'month') start.setDate(1);
  if (period === 'quarter') {
    start.setMonth(Math.floor(start.getMonth() / 3) * 3, 1);
  }
  return start;
}

function BillingDialog({ onClose, onCreated }) {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState('');
  const [cart, setCart] = useState([]);
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [customerName, setCustomerName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState(null);

  useEffect(() => {
    getProducts({ status: 'active' })
      .then(({ data }) => setProducts(data.products || []))
      .catch(() => setError('Could not load products. Check that the retail API is running.'));
  }, []);

  const visibleProducts = products.filter((product) =>
    `${product.name} ${product.sku} ${product.barcode}`.toLowerCase().includes(query.toLowerCase()),
  ).slice(0, 8);
  const subtotal = cart.reduce((sum, item) => sum + item.product.selling_price * item.quantity, 0);
  const tax = subtotal * 0.05;
  const total = subtotal + tax;

  const addProduct = (product) => {
    setCart((current) => {
      const existing = current.find((item) => item.product.id === product.id);
      if (existing) return current.map((item) => item.product.id === product.id ? { ...item, quantity: Math.min(item.quantity + 1, product.stock_quantity) } : item);
      if (product.stock_quantity < 1) return current;
      return [...current, { product, quantity: 1 }];
    });
  };

  const changeQuantity = (productId, quantity) => setCart((current) => current
    .map((item) => item.product.id === productId ? { ...item, quantity: Math.max(0, Math.min(quantity, item.product.stock_quantity)) } : item)
    .filter((item) => item.quantity > 0));

  const submit = async () => {
    if (!cart.length) return;
    setBusy(true);
    setError('');
    try {
      const { data } = await createSale({
        items: cart.map(({ product, quantity }) => ({ product_id: product.id, quantity })),
        payment_method: paymentMethod,
        customer_name: customerName,
      });
      setReceipt(data.sale);
      onCreated();
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'Billing could not be completed. Please review stock and try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="billing-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="billing-dialog" role="dialog" aria-modal="true" aria-labelledby="billing-title">
        <header className="billing-header">
          <div><span className="eyebrow">Point of sale</span><h2 id="billing-title">{receipt ? 'Bill generated' : 'Create a bill'}</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Close billing"><X size={18} /></button>
        </header>
        {receipt ? (
          <div className="receipt-view">
            <div className="receipt-success"><span><Check size={18} /></span><div><strong>Payment recorded</strong><small>{receipt.receipt_no}</small></div></div>
            <div className="receipt-items">{receipt.items?.map((item) => <div key={item.id}><span>{item.product_name} × {item.quantity}</span><strong>{money(item.total_price)}</strong></div>)}</div>
            <div className="receipt-total"><span>Total paid</span><strong>{money(receipt.total_amount)}</strong></div>
            <button className="button-secondary receipt-print" onClick={() => window.print()}><Printer size={16} /> Print receipt</button>
          </div>
        ) : (
          <>
            <div className="billing-content">
              <div className="billing-products">
                <label className="billing-search"><Search size={16} /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a product or scan a barcode" /></label>
                <div className="billing-product-list">
                  {visibleProducts.map((product) => <button className="billing-product" key={product.id} onClick={() => addProduct(product)} disabled={!product.stock_quantity}>
                    <span className="product-monogram"><Package size={17} /></span><span className="billing-product-name"><strong>{product.name}</strong><small>{product.sku} · {product.stock_quantity} in stock</small></span><strong>{money(product.selling_price)}</strong><Plus size={16} />
                  </button>)}
                  {!visibleProducts.length && <p className="billing-empty">No matching products.</p>}
                </div>
              </div>
              <aside className="billing-cart">
                <h3>Current bill <span>{cart.length} {cart.length === 1 ? 'item' : 'items'}</span></h3>
                <div className="cart-lines">{cart.map(({ product, quantity }) => <div className="cart-line" key={product.id}>
                  <div><strong>{product.name}</strong><small>{money(product.selling_price)} each</small><div className="quantity-control"><button onClick={() => changeQuantity(product.id, quantity - 1)} aria-label={`Remove one ${product.name}`}>−</button><span>{quantity}</span><button onClick={() => changeQuantity(product.id, quantity + 1)} aria-label={`Add one ${product.name}`}>+</button></div></div><b>{money(product.selling_price * quantity)}</b>
                </div>)}{!cart.length && <p className="billing-empty">Add products to start this bill.</p>}</div>
                <label className="billing-field">Customer name <input value={customerName} onChange={(event) => setCustomerName(event.target.value)} placeholder="Optional" /></label>
                <label className="billing-field">Payment method <select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}><option value="cash">Cash</option><option value="card">Card</option><option value="upi">UPI</option></select></label>
                <div className="bill-totals"><div><span>Subtotal</span><span>{money(subtotal)}</span></div><div><span>Tax (5%)</span><span>{money(tax)}</span></div><div className="bill-grand-total"><strong>Total</strong><strong>{money(total)}</strong></div></div>
                {error && <p className="form-error" role="alert">{error}</p>}
                <button className="button-primary bill-submit" onClick={submit} disabled={busy || !cart.length}>{busy ? <LoaderCircle className="spin" size={17} /> : <BadgeIndianRupee size={17} />}{busy ? 'Generating bill…' : 'Generate bill'}</button>
              </aside>
            </div>
            {error && <p className="form-error billing-load-error" role="alert">{error}</p>}
          </>
        )}
      </section>
    </div>
  );
}

export default function Dashboard() {
  const [period, setPeriod] = useState('week');
  const [now] = useState(() => new Date());
  const [sales, setSales] = useState([]);
  const [returns, setReturns] = useState([]);
  const [underperforming, setUnderperforming] = useState([]);
  const [recommendations, setRecommendations] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [billingOpen, setBillingOpen] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      const results = await Promise.allSettled([
        getSales({ limit: 500 }),
        getInventoryTransactions({ limit: 1000 }),
        getUnderperformingProducts(),
      ]);
      if (results[0].status === 'fulfilled') setSales(results[0].value.data.sales || []);
      else setLoadError('Sales data is unavailable. Start the retail API and refresh.');
      if (results[1].status === 'fulfilled') setReturns((results[1].value.data || []).filter((tx) => tx.transaction_type === 'return'));
      if (results[2].status === 'fulfilled') setUnderperforming(results[2].value.data.underperforming_products || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const periodData = useMemo(() => {
    const start = getPeriodStart(period, now);
    const filtered = sales.filter((sale) => new Date(sale.created_at) >= start && new Date(sale.created_at) <= now);
    const chartBuckets = new Map();
    const bucketFor = (date) => {
      const keyDate = new Date(date);
      if (period === 'week') return { key: keyDate.toISOString().slice(0, 10), label: keyDate.toLocaleDateString('en-IN', { weekday: 'short' }) };
      if (period === 'month') {
        const weekNumber = Math.floor((keyDate.getDate() - 1) / 7) + 1;
        return { key: `${keyDate.getFullYear()}-${keyDate.getMonth()}-${weekNumber}`, label: `Week ${weekNumber}` };
      }
      return { key: `${keyDate.getFullYear()}-${keyDate.getMonth()}`, label: keyDate.toLocaleDateString('en-IN', { month: 'short' }) };
    };
    filtered.forEach((sale) => {
      const bucket = bucketFor(sale.created_at);
      const current = chartBuckets.get(bucket.key) || { key: bucket.key, label: bucket.label, revenue: 0, units: 0, products: new Set() };
      current.revenue += Number(sale.total_amount || 0);
      (sale.items || []).forEach((item) => { current.units += Number(item.quantity || 0); current.products.add(item.product_id); });
      chartBuckets.set(bucket.key, current);
    });
    const periodReturns = returns.filter((tx) => new Date(tx.created_at) >= start && new Date(tx.created_at) <= now);
    const returnUnits = periodReturns.reduce((total, tx) => total + Math.abs(Number(tx.quantity || 0)), 0);
    const returnBuckets = new Map();
    periodReturns.forEach((tx) => {
      const bucket = bucketFor(tx.created_at);
      returnBuckets.set(bucket.key, (returnBuckets.get(bucket.key) || 0) + Math.abs(Number(tx.quantity || 0)));
      if (!chartBuckets.has(bucket.key)) chartBuckets.set(bucket.key, { key: bucket.key, label: bucket.label, revenue: 0, units: 0, products: new Set() });
    });
    const buckets = [...chartBuckets.values()].map((bucket) => ({ ...bucket, products: bucket.products.size, returns: returnBuckets.get(bucket.key) || 0 }));
    const revenue = filtered.reduce((total, sale) => total + Number(sale.total_amount || 0), 0);
    const units = filtered.reduce((total, sale) => total + (sale.items || []).reduce((itemTotal, item) => itemTotal + Number(item.quantity || 0), 0), 0);
    const distinctProducts = new Set(filtered.flatMap((sale) => (sale.items || []).map((item) => item.product_id))).size;
    return { buckets, revenue, units, distinctProducts, returnUnits, billCount: filtered.length, start };
  }, [now, period, sales, returns]);

  const runReplacementSearch = async (productId) => {
    setRecommendations((current) => ({ ...current, [productId]: { loading: true } }));
    try {
      const { data } = await searchReplacements(productId);
      setRecommendations((current) => ({ ...current, [productId]: { results: data.recommendations || [] } }));
    } catch (error) {
      setRecommendations((current) => ({ ...current, [productId]: { error: error.response?.data?.error || 'Could not get replacement ideas.' } }));
    }
  };

  const rangeLabel = period === 'week' ? 'This week' : period === 'month' ? 'This month' : 'This quarter';
  const replacements = underperforming.slice(0, 4);

  return (
    <div className="dashboard">
      <header className="dashboard-heading">
        <div><p className="eyebrow">STORE OVERVIEW</p><h1>Welcome back</h1><p className="dashboard-subtitle">Here’s your overall store performance today.</p></div>
        <button className="button-primary billing-launch" onClick={() => setBillingOpen(true)}><BadgeIndianRupee size={18} /> Create bill</button>
      </header>

      {loadError && <div className="dashboard-alert" role="status"><AlertCircle size={17} />{loadError}<button onClick={loadDashboard}>Retry</button></div>}

      <section className="sales-section" aria-labelledby="sales-title">
        <div className="section-heading">
          <div><span className="section-kicker"><Activity size={15} /> SALES OVERVIEW</span><h2 id="sales-title">Sales funnel</h2><p>Revenue, product movement, and returns for {rangeLabel.toLowerCase()}.</p></div>
          <div className="period-switch" role="group" aria-label="Sales period">
            {[['week', 'Week'], ['month', 'Month'], ['quarter', 'Quarter']].map(([value, label]) => <button key={value} className={period === value ? 'selected' : ''} onClick={() => setPeriod(value)} aria-pressed={period === value}>{label}</button>)}
          </div>
        </div>
        <div className="sales-layout">
          <div className="sales-chart-area">
            <div className="sales-chart-legend"><span><i className="legend-revenue" />Revenue</span><span><i className="legend-products" />Units sold</span><span><i className="legend-returns" />Units returned</span></div>
            <div className="sales-chart">
              {loading ? <div className="chart-state"><LoaderCircle className="spin" size={22} />Loading sales…</div> : periodData.buckets.length ? <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={periodData.buckets} margin={{ top: 8, right: 8, left: -12, bottom: 2 }}>
                  <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="4 6" />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis yAxisId="revenue" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickFormatter={(value) => value >= 100000 ? `₹${(value / 100000).toFixed(1)}L` : `₹${Math.round(value / 1000)}k`} />
                  <YAxis yAxisId="units" orientation="right" hide />
                  <Tooltip contentStyle={{ background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 10 }} formatter={(value, name) => [name === 'Revenue' ? money(value) : value, name]} />
                  <Bar yAxisId="revenue" dataKey="revenue" name="Revenue" fill="var(--accent-2)" radius={[5, 5, 0, 0]} maxBarSize={42} />
                  <Line yAxisId="units" dataKey="units" name="Units sold" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3, fill: 'var(--accent)' }} />
                  <Line yAxisId="units" dataKey="returns" name="Units returned" stroke="var(--danger)" strokeWidth={2} strokeDasharray="5 4" dot={false} />
                </ComposedChart>
              </ResponsiveContainer> : <div className="chart-state"><ClipboardList size={22} /><span>No sales recorded {rangeLabel.toLowerCase()}.</span></div>}
            </div>
            <p className="chart-caption">Sales are from completed POS bills since {formatDate(periodData.start)}. Return counts use recorded inventory return transactions.</p>
          </div>
          <aside className="sales-summary">
            <div className="summary-primary"><span>Total revenue</span><strong>{money(periodData.revenue)}</strong><small>{periodData.billCount} completed {periodData.billCount === 1 ? 'bill' : 'bills'}</small><span className="summary-orb"><CircleDollarSign size={21} /></span></div>
            <div className="summary-stat"><span className="summary-icon products-icon"><Boxes size={17} /></span><div><small>Products sold</small><strong>{periodData.units.toLocaleString()} <em>units</em></strong><span>{periodData.distinctProducts} different products</span></div></div>
            <div className="summary-stat"><span className="summary-icon returns-icon"><RotateCcw size={17} /></span><div><small>Products returned</small><strong>{periodData.returnUnits.toLocaleString()} <em>units</em></strong><span>Recorded in inventory</span></div></div>
          </aside>
        </div>
      </section>

      <section className="replacement-section" aria-labelledby="replacement-title">
        <div className="section-heading replacement-heading">
          <div><span className="section-kicker"><Sparkles size={15} /> DECISION SUPPORT</span><h2 id="replacement-title">AI product replacements</h2><p>Find alternatives for slow-moving stock and review the rationale before acting.</p></div>
          <span className="count-badge"><Package size={14} />{underperforming.length} products to review</span>
        </div>
        {loading ? <div className="replacement-empty"><LoaderCircle className="spin" size={20} />Scanning inventory health…</div> : replacements.length ? <div className="replacement-list">
          {replacements.map((entry) => {
            const product = entry.product;
            const search = recommendations[product.id];
            return <article className="replacement-row" key={product.id}>
              <div className="replacement-product-icon"><Package size={20} /></div>
              <div className="replacement-product-info"><strong>{product.name}</strong><span>{product.sku} <i /> {product.category}</span></div>
              <div className="replacement-metric"><small>Stock</small><strong>{product.stock_quantity} units</strong></div>
              <div className="replacement-metric capital-metric"><small>Capital tied up</small><strong>{money(entry.trapped_capital)}</strong></div>
              <div className="replacement-action">
                {search?.results?.length ? <div className="replacement-result"><strong>{search.results[0].recommended_title}</strong><span>{search.results[0].reasoning || 'Alternative found for review'}</span></div> : <button className="replacement-button" disabled={search?.loading} onClick={() => runReplacementSearch(product.id)}>{search?.loading ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}{search?.loading ? 'Finding…' : 'Find replacement'}<ArrowUpRight size={14} /></button>}
                {search?.error && <small className="replacement-error">{search.error}</small>}
              </div>
            </article>;
          })}
        </div> : <div className="replacement-empty"><Check size={18} /><span>No products currently meet the slow-stock replacement criteria.</span></div>}
        <div className="replacement-footnote"><AlertCircle size={14} />Suggestions are decision support. Review evidence and approve any catalog changes yourself.</div>
      </section>

      <section className="dashboard-next-steps" aria-label="Plan-aligned dashboard ideas">
        <div><span className="next-icon"><ArrowDownRight size={17} /></span><div><strong>Keep decisions explainable</strong><p>Show the forecast, stock cover, and reason behind each reorder or markdown.</p></div></div>
        <div><span className="next-icon"><Activity size={17} /></span><div><strong>Watch model health</strong><p>Bring drift status and forecast accuracy into the daily operating view.</p></div></div>
        <div><span className="next-icon"><Boxes size={17} /></span><div><strong>Prioritize inventory risk</strong><p>Surface stockout risk and trapped capital beside the sales trend.</p></div></div>
      </section>
      {billingOpen && <BillingDialog onClose={() => setBillingOpen(false)} onCreated={loadDashboard} />}
    </div>
  );
}
