import { useEffect, useState, useMemo } from 'react';
import { Loader2, TrendingUp, AlertTriangle, ChevronDown, Filter, Download, Info, Clock, Warehouse, DollarSign } from 'lucide-react';
import { format } from 'date-fns';
import { getDashboardData } from '../services/api';
import './SteadyLowVolume.css';

export default function SteadyLowVolume() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [divisionFilter, setDivisionFilter] = useState('all');
  const [consistencyFilter, setConsistencyFilter] = useState('all');
  const [monthlyRange, setMonthlyRange] = useState([0, 10]);
  const [sortConfig, setSortConfig] = useState({ key: 'consistency_score', direction: 'desc' });
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const PAGE_SIZE = 50;

  const fetchData = async () => {
    try {
      setLoading(true);
      // In production: const response = await getSteadyProducts({ min_months: 6, max_cv: 0.3, max_monthly_mean: 5 });
      const mockData = generateMockSteadyProducts();
      setProducts(mockData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const divisions = useMemo(() => ['all', ...new Set(products.map(p => p.product_division)).sort()], [products]);

  const filteredProducts = useMemo(() => {
    return products
      .filter(p => {
        const matchesSearch = p.product_description.toLowerCase().includes(search.toLowerCase()) ||
          p.product_no.toLowerCase().includes(search.toLowerCase());
        const matchesDivision = divisionFilter === 'all' || p.product_division === divisionFilter;
        const matchesConsistency = consistencyFilter === 'all' ||
          (consistencyFilter === 'high' && p.consistency_score > 0.7) ||
          (consistencyFilter === 'medium' && p.consistency_score > 0.4 && p.consistency_score <= 0.7) ||
          (consistencyFilter === 'low' && p.consistency_score <= 0.4);
        const matchesMonthly = p.avg_monthly_qty >= monthlyRange[0] && p.avg_monthly_qty <= monthlyRange[1];
        return matchesSearch && matchesDivision && matchesConsistency && matchesMonthly;
      })
      .sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
  }, [products, search, divisionFilter, consistencyFilter, monthlyRange, sortConfig]);

  const paginatedProducts = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredProducts.slice(start, start + PAGE_SIZE);
  }, [filteredProducts, page]);

  const totalPages = Math.ceil(filteredProducts.length / PAGE_SIZE);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const stats = useMemo(() => {
    const steady = products.filter(p => p.is_steady_low_volume);
    return {
      total: products.length,
      steady: steady.length,
      highConsistency: steady.filter(p => p.consistency_score > 0.7).length,
      totalMonthlyQty: steady.reduce((sum, p) => sum + p.avg_monthly_qty, 0),
      avgConsistency: steady.length > 0 ? (steady.reduce((s, p) => s + p.consistency_score, 0) / steady.length * 100).toFixed(0) : 0,
      totalInventoryValue: steady.reduce((sum, p) => sum + p.qty_on_hand * p.unit_cost, 0),
    };
  }, [products]);

  if (loading) {
    return (
      <div className="steady-loading">
        <Loader2 size={48} className="spinner" />
        <p>Analyzing steady low-volume products...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="steady-error">
        <AlertTriangle size={48} color="var(--danger)" />
        <h2>Failed to load steady products</h2>
        <p>{error}</p>
        <button className="btn" onClick={fetchData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="steady-low-volume">
      <div className="steady-header">
        <div>
          <h1>Steady Low-Volume Products</h1>
          <p className="subtitle">
            {'Products with consistent low monthly sales (CV < 30%, 2-5 units/month) \u2014 likely niche loyal buyers'}
          </p>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" disabled={selectedIds.size === 0}>
            <Download size={16} /> Export
          </button>
        </div>
      </div>

      <div className="steady-info-banner">
        <Info size={20} />
        <div>
          <strong>Detection Criteria:</strong> 6+ months of data {'\u2022'} Monthly CV {'<'} 30% {'\u2022'} Avg 2-5 units/month {'\u2022'} Non-zero in 80%+ months
        </div>
      </div>

      <div className="stats-bar">
        <StatCard label="Total Products" value={stats.total} icon={<PackageSearch size={20} />} />
        <StatCard label="Steady Low-Volume" value={stats.steady} variant="success" icon={<TrendingUp size={20} />} />
        <StatCard label="High Consistency (>70%)" value={stats.highConsistency} variant="success" icon={<TrendingUp size={20} />} />
        <StatCard label="Avg Consistency" value={`${stats.avgConsistency}%`} icon={<TrendingUp size={20} />} />
        <StatCard label="Total Monthly Demand" value={stats.totalMonthlyQty.toFixed(0)} icon={<Warehouse size={20} />} />
        <StatCard label="Inventory Value at Risk" value={`$${(stats.totalInventoryValue / 1000).toFixed(0)}K`} variant="warning" icon={<DollarSign size={20} />} />
      </div>

      <div className="filters-bar">
        <div className="search-box">
          <Filter size={18} />
          <input
            type="text"
            placeholder="Search products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <label>Division</label>
          <select value={divisionFilter} onChange={(e) => setDivisionFilter(e.target.value)}>
            {divisions.map(d => <option key={d} value={d}>{d === 'all' ? 'All Divisions' : d}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Consistency</label>
          <select value={consistencyFilter} onChange={(e) => setConsistencyFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="high">High ({">70%"})</option>
            <option value="medium">Medium (40-70%)</option>
            <option value="low">Low ({'<40%'})</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Avg Monthly Qty</label>
          <div className="range-inputs">
            <input type="number" min="0" max="10" step="0.5" value={monthlyRange[0]} onChange={(e) => setMonthlyRange([Number(e.target.value), monthlyRange[1]])} placeholder="Min" />
            <span>–</span>
            <input type="number" min="0" max="10" step="0.5" value={monthlyRange[1]} onChange={(e) => setMonthlyRange([monthlyRange[0], Number(e.target.value)])} placeholder="Max" />
          </div>
        </div>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              {[
                { key: 'product_no', label: 'Product No' },
                { key: 'product_description', label: 'Product' },
                { key: 'product_division', label: 'Division' },
                { key: 'product_category', label: 'Category' },
                { key: 'store', label: 'Store' },
                { key: 'avg_monthly_qty', label: 'Avg Monthly', numeric: true },
                { key: 'consistency_score', label: 'Consistency', numeric: true },
                { key: 'months_active', label: 'Months Active', numeric: true },
                { key: 'zero_months', label: 'Zero Months', numeric: true },
                { key: 'cv_monthly', label: 'Monthly CV', numeric: true },
                { key: 'total_qty_11mo', label: 'Total (11mo)', numeric: true },
                { key: 'qty_on_hand', label: 'On Hand', numeric: true },
                { key: 'weeks_supply', label: 'Weeks Supply', numeric: true },
                { key: 'unit_cost', label: 'Unit Cost', numeric: true },
                { key: 'inventory_value', label: 'Inv Value', numeric: true },
                { key: 'recommendation', label: 'Action' },
              ].map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="th-content">
                    <span>{col.label}</span>
                    {sortConfig.key === col.key && (
                      <ChevronDown size={14} className={sortConfig.direction === 'asc' ? 'asc' : ''} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedProducts.map((product) => (
              <tr key={product.product_no}>
                <td><code>{product.product_no}</code></td>
                <td className="description-cell">
                  <span className="desc-main">{product.product_description}</span>
                  <span className="desc-meta">{product.product_segment}</span>
                </td>
                <td>{product.product_division}</td>
                <td>{product.product_category}</td>
                <td>{product.store}</td>
                <td className="numeric">{product.avg_monthly_qty.toFixed(1)}</td>
                <td className="numeric">
                  <span className={`consistency-badge ${product.consistency_score > 0.7 ? 'high' : product.consistency_score > 0.4 ? 'medium' : 'low'}`}>
                    {(product.consistency_score * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="numeric">{product.months_active}</td>
                <td className="numeric">{product.zero_months}</td>
                <td className="numeric">{(product.cv_monthly * 100).toFixed(1)}%</td>
                <td className="numeric">{product.total_qty_11mo.toLocaleString()}</td>
                <td className="numeric">{product.qty_on_hand.toLocaleString()}</td>
                <td className="numeric">{product.weeks_supply?.toFixed(1) ?? '—'}</td>
                <td className="numeric">${product.unit_cost.toFixed(2)}</td>
                <td className="numeric">${product.inventory_value.toLocaleString()}</td>
                <td>
                  <span className={`action-badge action-${product.recommendation}`}>
                    {product.recommendation.toUpperCase()}
                  </span>
                </td>
              </tr>
            ))}
            {paginatedProducts.length === 0 && (
              <tr>
                <td colSpan={16} className="empty-row">No products match your filters</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
            Previous
          </button>
          <span className="pagination-info">
            Page {page} of {totalPages} ({filteredProducts.length.toLocaleString()} products)
          </span>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
            Next
          </button>
        </div>
      )}

      <div className="steady-insights">
        <h3>Key Insights</h3>
        <div className="insights-grid">
          <InsightCard
            title="Niche Opportunity"
            description={`${stats.steady} products show steady low-volume demand. These likely have loyal repeat buyers who purchase consistently.` }
            icon={<TrendingUp size={24} />}
            variant="success"
          />
          <InsightCard
            title="Inventory Optimization"
            description={`Total inventory value of ${(stats.totalInventoryValue / 1000).toFixed(0)}K tied up in steady products. Consider reducing safety stock for high-consistency items.` }
            icon={<Warehouse size={24} />}
            variant="warning"
          />
          <InsightCard
            title="Reorder Strategy"
            description={`For high-consistency products (>70%), use fixed reorder points based on avg monthly demand × lead time instead of ML forecasts.` }
            icon={<Clock size={24} />}
            variant="info"
          />
          <InsightCard
            title="Category Concentration"
            description={`Steady products concentrated in ${Math.min(3, stats.steady)} categories. Review if category-level contracts can secure better terms.` }
            icon={<DollarSign size={24} />}
            variant="neutral"
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, variant, icon }) {
  const colors = {
    success: { bg: 'var(--success-dim)', color: 'var(--success)' },
    warning: { bg: 'var(--warning-dim)', color: 'var(--warning)' },
    info: { bg: 'var(--accent-dim)', color: 'var(--accent-2)' },
    neutral: { bg: 'rgba(145, 160, 189, 0.15)', color: 'var(--text-muted)' },
    default: { bg: 'var(--accent-dim)', color: 'var(--accent)' },
  };
  const c = colors[variant || 'default'];

  return (
    <div className="stat-card" style={{ '--stat-color': c.color, '--stat-bg': c.bg }}>
      <div className="stat-icon" style={{ background: c.bg, color: c.color }}>{icon}</div>
      <div className="stat-content">
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

function InsightCard({ title, description, icon, variant }) {
  const colors = {
    success: { bg: 'var(--success-dim)', border: 'var(--success)', icon: 'var(--success)' },
    warning: { bg: 'var(--warning-dim)', border: 'var(--warning)', icon: 'var(--warning)' },
    info: { bg: 'var(--accent-dim)', border: 'var(--accent-2)', icon: 'var(--accent-2)' },
    neutral: { bg: 'rgba(145, 160, 189, 0.1)', border: 'var(--text-muted)', icon: 'var(--text-muted)' },
  };
  const c = colors[variant || 'info'];

  return (
    <div className="insight-card" style={{ '--insight-bg': c.bg, '--insight-border': c.border, '--insight-icon': c.icon }}>
      <div className="insight-icon">{icon}</div>
      <div className="insight-content">
        <h4>{title}</h4>
        <p>{description}</p>
      </div>
    </div>
  );
}

// Mock data generator
function generateMockSteadyProducts() {
  const divisions = ['Scholar Footwear', 'Femme Footwear', 'Junior Apparel'];
  const categories = {
    'Scholar Footwear': ['Trailblazer', 'Flight Classic', 'Boot Collection', 'Court Casual'],
    'Femme Footwear': ['Trailblazer', 'Flight Classic', 'Court Casual', 'Boot Collection'],
    'Junior Apparel': ['Crop Pants', 'Printed Tees', 'Denim Classics', 'Cozy Pullovers'],
  };
  const stores = Array.from({ length: 40 }, (_, i) => `STR-${String(1000 + i).padStart(4, '0')}`);
  const actions = ['reorder', 'markdown', 'monitor', 'hold'];
  const products = [];

  // Generate ~200 steady low-volume products
  for (let i = 0; i < 200; i++) {
    const division = divisions[Math.floor(Math.random() * divisions.length)];
    const catList = categories[division];
    const category = catList[Math.floor(Math.random() * catList.length)];
    const subcategory = `${division} ${category} ${['Zephyr', 'Equilibrium', 'Summit', 'Varied'][Math.floor(Math.random() * 4)]}`;
    const segment = `SEG-${String(500000 + i).padStart(6, '0')} ${subcategory}`;
    const productNo = `PROD-${String(100000 + i).padStart(6, '0')}`;
    const store = stores[Math.floor(Math.random() * stores.length)];

    // Steady low-volume: 2-5 units/month, low CV
    const avgMonthly = 2 + Math.random() * 3;
    const cv = 0.1 + Math.random() * 0.2; // 10-30% CV
    const consistency = 1 - cv; // High consistency = low CV
    const monthsActive = Math.floor(8 + Math.random() * 4); // 8-11 months
    const zeroMonths = 11 - monthsActive;
    const totalQty = Math.round(avgMonthly * 11);

    products.push({
      product_no: productNo,
      product_description: subcategory,
      product_division: division,
      product_category: category,
      product_subcategory: subcategory,
      product_segment: segment,
      store,
      avg_monthly_qty: avgMonthly,
      consistency_score: consistency,
      months_active: monthsActive,
      zero_months: zeroMonths,
      cv_monthly: cv,
      total_qty_11mo: totalQty,
      qty_on_hand: Math.max(0, Math.round(Math.random() * 30)),
      weeks_supply: Math.random() > 0.3 ? (2 + Math.random() * 8).toFixed(1) : null,
      unit_cost: 15 + Math.random() * 60,
      inventory_value: 0,
      recommendation: actions[Math.floor(Math.random() * actions.length)],
      is_steady_low_volume: true,
    });
  }

  // Add some non-steady products for comparison
  for (let i = 0; i < 100; i++) {
    const division = divisions[Math.floor(Math.random() * divisions.length)];
    const catList = categories[division];
    const category = catList[Math.floor(Math.random() * catList.length)];
    const subcategory = `${division} ${category} ${['Zephyr', 'Equilibrium', 'Summit', 'Varied'][Math.floor(Math.random() * 4)]}`;
    const segment = `SEG-${String(600000 + i).padStart(6, '0')} ${subcategory}`;
    const productNo = `PROD-${String(200000 + i).padStart(6, '0')}`;
    const store = stores[Math.floor(Math.random() * stores.length)];

    const avgMonthly = Math.random() * 20;
    const cv = 0.3 + Math.random() * 0.7; // Higher CV
    const consistency = Math.max(0.1, 1 - cv);
    const monthsActive = Math.floor(Math.random() * 11) + 1;
    const zeroMonths = 11 - monthsActive;
    const totalQty = Math.round(avgMonthly * 11);

    products.push({
      product_no: productNo,
      product_description: subcategory,
      product_division: division,
      product_category: category,
      product_subcategory: subcategory,
      product_segment: segment,
      store,
      avg_monthly_qty: avgMonthly,
      consistency_score: consistency,
      months_active: monthsActive,
      zero_months: zeroMonths,
      cv_monthly: cv,
      total_qty_11mo: totalQty,
      qty_on_hand: Math.max(0, Math.round(Math.random() * 50)),
      weeks_supply: Math.random() > 0.3 ? (1 + Math.random() * 12).toFixed(1) : null,
      unit_cost: 15 + Math.random() * 60,
      inventory_value: 0,
      recommendation: actions[Math.floor(Math.random() * actions.length)],
      is_steady_low_volume: false,
    });
  }

  // Calculate inventory value
  products.forEach(p => { p.inventory_value = p.qty_on_hand * p.unit_cost; });

  return products.sort((a, b) => b.consistency_score - a.consistency_score);
}

// Reuse PackageSearch from lucide-react
const PackageSearch = ({ size }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>;
