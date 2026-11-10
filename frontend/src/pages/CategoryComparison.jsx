import { useEffect, useState, useMemo } from 'react';
import { Loader2, BarChart2, TrendingUp, TrendingDown, AlertTriangle, ChevronDown, ExternalLink } from 'lucide-react';
import { format } from 'date-fns';
import { getDashboardData } from '../services/api';
import './CategoryComparison.css';

export default function CategoryComparison() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedSubcategory, setSelectedSubcategory] = useState('all');
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'chart'
  const [sortConfig, setSortConfig] = useState({ key: 'total_qty', direction: 'desc' });

  const fetchData = async () => {
    try {
      setLoading(true);
      // In production: const response = await getCategoryComparison(category, subcategory);
      const mockData = generateMockCategoryData();
      setData(mockData);
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

  const categories = useMemo(() => {
    if (!data) return [];
    const cats = [...new Set(data.products.map(p => p.product_division))].sort();
    return ['all', ...cats];
  }, [data]);

  const subcategories = useMemo(() => {
    if (!data || selectedCategory === 'all') return ['all'];
    const subs = [...new Set(
      data.products
        .filter(p => p.product_division === selectedCategory)
        .map(p => p.product_category)
    )].sort();
    return ['all', ...subs];
  }, [data, selectedCategory]);

  const filteredProducts = useMemo(() => {
    if (!data) return [];
    return data.products
      .filter(p => (selectedCategory === 'all' || p.product_division === selectedCategory))
      .filter(p => (selectedSubcategory === 'all' || p.product_category === selectedSubcategory))
      .sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
  }, [data, selectedCategory, selectedSubcategory, sortConfig]);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const divisionStats = useMemo(() => {
    if (!data) return [];
    const stats = {};
    data.products.forEach(p => {
      if (!stats[p.product_division]) {
        stats[p.product_division] = { products: 0, total_qty: 0, total_revenue: 0, avg_consistency: 0, count: 0 };
      }
      stats[p.product_division].products++;
      stats[p.product_division].total_qty += p.total_qty;
      stats[p.product_division].total_revenue += p.total_revenue;
      stats[p.product_division].avg_consistency += p.consistency_score;
      stats[p.product_division].count++;
    });
    return Object.entries(stats).map(([division, s]) => ({
      division,
      products: s.products,
      total_qty: s.total_qty,
      total_revenue: s.total_revenue,
      avg_consistency: (s.avg_consistency / s.count * 100).toFixed(0) + '%',
      avg_monthly_per_product: (s.total_qty / s.products / 11).toFixed(1),
    })).sort((a, b) => b.total_qty - a.total_qty);
  }, [data]);

  if (loading) {
    return (
      <div className="comparison-loading">
        <Loader2 size={48} className="spinner" />
        <p>Loading category comparison...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="comparison-error">
        <AlertTriangle size={48} color="var(--danger)" />
        <h2>Failed to load comparison</h2>
        <p>{error}</p>
        <button className="btn" onClick={fetchData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="category-comparison">
      <div className="comparison-header">
        <div>
          <h1>Category Comparison</h1>
          <p className="subtitle">Compare products within divisions and categories to identify winners and losers</p>
        </div>
        <div className="header-controls">
          <div className="view-toggle" role="radiogroup" aria-label="View mode">
            <button
              role="radio"
              aria-checked={viewMode === 'table'}
              className={viewMode === 'table' ? 'active' : ''}
              onClick={() => setViewMode('table')}
            >
              <BarChart2 size={16} /> Table
            </button>
            <button
              role="radio"
              aria-checked={viewMode === 'chart'}
              className={viewMode === 'chart' ? 'active' : ''}
              onClick={() => setViewMode('chart')}
            >
              <TrendingUp size={16} /> Chart
            </button>
          </div>
        </div>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Division</label>
          <div className="select-wrapper">
            <select value={selectedCategory} onChange={(e) => { setSelectedCategory(e.target.value); setSelectedSubcategory('all'); }}>
              {categories.map(c => <option key={c} value={c}>{c === 'all' ? 'All Divisions' : c}</option>)}
            </select>
            <ChevronDown size={16} />
          </div>
        </div>
        <div className="filter-group">
          <label>Category</label>
          <div className="select-wrapper">
            <select value={selectedSubcategory} onChange={(e) => setSelectedSubcategory(e.target.value)} disabled={selectedCategory === 'all'}>
              {subcategories.map(s => <option key={s} value={s}>{s === 'all' ? 'All Categories' : s}</option>)}
            </select>
            <ChevronDown size={16} />
          </div>
        </div>
        <div className="filter-info">
          Showing <strong>{filteredProducts.length}</strong> of {data?.products.length || 0} products
        </div>
      </div>

      <div className="division-summary">
        <h3>Division Overview</h3>
        <div className="summary-grid">
          {divisionStats.map((stat) => (
            <div key={stat.division} className="summary-card">
              <div className="summary-title">{stat.division}</div>
              <div className="summary-metrics">
                <div className="metric"><span className="metric-value">{stat.products}</span><span className="metric-label">Products</span></div>
                <div className="metric"><span className="metric-value">{stat.total_qty.toLocaleString()}</span><span className="metric-label">Total Qty</span></div>
                <div className="metric"><span className="metric-value">${stat.total_revenue.toLocaleString()}</span><span className="metric-label">Revenue</span></div>
                <div className="metric"><span className="metric-value">{stat.avg_consistency}</span><span className="metric-label">Avg Consistency</span></div>
                <div className="metric"><span className="metric-value">{stat.avg_monthly_per_product}</span><span className="metric-label">Monthly/Product</span></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {viewMode === 'table' ? (
        <ProductTable
          products={filteredProducts}
          sortConfig={sortConfig}
          onSort={handleSort}
        />
      ) : (
        <ComparisonChart products={filteredProducts} />
      )}
    </div>
  );
}

function ProductTable({ products, sortConfig, onSort }) {
  if (products.length === 0) {
    return (
      <div className="empty-state">
        <BarChart2 size={48} color="var(--text-muted)" />
        <h3>No products match your filters</h3>
        <p className="muted">Try adjusting your division or category selection.</p>
      </div>
    );
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            {[
              { key: 'product_no', label: 'Product No' },
              { key: 'product_description', label: 'Product' },
              { key: 'product_category', label: 'Category' },
              { key: 'product_subcategory', label: 'Subcategory' },
              { key: 'store', label: 'Store' },
              { key: 'total_qty', label: 'Total Qty (11mo)', numeric: true },
              { key: 'avg_monthly', label: 'Avg Monthly', numeric: true },
              { key: 'consistency_score', label: 'Consistency', numeric: true },
              { key: 'total_revenue', label: 'Revenue', numeric: true },
              { key: 'avg_price', label: 'Avg Price', numeric: true },
              { key: 'promo_dependency', label: 'Promo %', numeric: true },
              { key: 'stockout_risk', label: 'Stockout Risk', numeric: true },
              { key: 'recommendation', label: 'Action' },
            ].map((col) => (
              <th
                key={col.key}
                onClick={() => onSort(col.key)}
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
          {products.map((product, idx) => (
            <tr key={product.product_no}>
              <td><code>{product.product_no}</code></td>
              <td className="description-cell">
                <span className="desc-main">{product.product_description}</span>
                <span className="desc-meta">{product.product_segment}</span>
              </td>
              <td>{product.product_category}</td>
              <td>{product.product_subcategory}</td>
              <td>{product.store}</td>
              <td className="numeric">{product.total_qty.toLocaleString()}</td>
              <td className="numeric">{product.avg_monthly.toFixed(1)}</td>
              <td className="numeric">
                <span className={`consistency-badge ${product.consistency_score > 0.7 ? 'high' : product.consistency_score > 0.4 ? 'medium' : 'low'}`}>
                  {(product.consistency_score * 100).toFixed(0)}%
                </span>
              </td>
              <td className="numeric">${product.total_revenue.toLocaleString()}</td>
              <td className="numeric">${product.avg_price.toFixed(2)}</td>
              <td className="numeric">{(product.promo_dependency * 100).toFixed(0)}%</td>
              <td className="numeric">
                <span className={`risk-badge ${product.stockout_risk > 0.5 ? 'high' : product.stockout_risk > 0.2 ? 'medium' : 'low'}`}>
                  {(product.stockout_risk * 100).toFixed(0)}%
                </span>
              </td>
              <td>
                <span className={`action-badge action-${product.recommendation}`}>
                  {product.recommendation.toUpperCase()}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ComparisonChart({ products }) {
  const topProducts = products.slice(0, 20);
  const maxQty = Math.max(...topProducts.map(p => p.total_qty), 1);
  const chartHeight = 300;

  return (
    <div className="chart-container">
      <h3>Top 20 Products by Total Quantity</h3>
      <svg width="100%" height={chartHeight + 60} viewBox={`0 0 ${topProducts.length * 40 + 80} ${chartHeight + 60}`} className="bar-chart">
        {topProducts.map((product, idx) => {
          const x = 50 + idx * 40;
          const barH = (product.total_qty / maxQty) * chartHeight;
          const y = 30 + chartHeight - barH;
          const color = product.consistency_score > 0.7 ? 'var(--success)' : product.consistency_score > 0.4 ? 'var(--warning)' : 'var(--danger)';
          return (
            <g key={product.product_no} style={{ cursor: 'pointer' }}>
              <rect x={x} y={y} width={30} height={barH} fill={color} rx={2} opacity="0.85" />
              <text x={x + 15} y={30 + chartHeight + 15} textAnchor="middle" fontSize="9" fill="var(--text-muted)" transform={`rotate(-45, ${x + 15}, ${30 + chartHeight + 15})`}>
                {product.product_description.slice(0, 20)}
              </text>
              <text x={x + 15} y={y - 4} textAnchor="middle" fontSize="10" fill="var(--text)">
                {product.total_qty > 0 ? product.total_qty : ''}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="chart-legend">
        <span className="legend-item"><span className="legend-color" style={{ background: 'var(--success)' }}></span>High Consistency ({">70%"})</span>
        <span className="legend-item"><span className="legend-color" style={{ background: 'var(--warning)' }}></span>Medium Consistency (40-70%)</span>
        <span className="legend-item"><span className="legend-color" style={{ background: 'var(--danger)' }}></span>Low Consistency ({'<40%'})</span>
      </div>
    </div>
  );
}

// Mock data generator
function generateMockCategoryData() {
  const divisions = ['Scholar Footwear', 'Femme Footwear', 'Junior Apparel'];
  const categories = {
    'Scholar Footwear': ['Trailblazer', 'Flight Classic', 'Boot Collection', 'Court Casual', 'Canvas Styles', 'Retro Legend', 'Modern Legend', 'Trainer'],
    'Femme Footwear': ['Trailblazer', 'Flight Classic', 'Court Casual', 'Boot Collection', 'Retro Legend'],
    'Junior Apparel': ['Crop Pants', 'Printed Tees', 'Denim Classics', 'Cozy Pullovers', 'Cozy Trousers', 'Crew Tees', 'Light Shells'],
  };
  const stores = Array.from({ length: 40 }, (_, i) => `STR-${String(1000 + i).padStart(4, '0')}`);
  const actions = ['reorder', 'markdown', 'monitor', 'hold'];
  const products = [];

  for (let i = 0; i < 2326; i++) {
    const division = divisions[Math.floor(Math.random() * divisions.length)];
    const catList = categories[division];
    const category = catList[Math.floor(Math.random() * catList.length)];
    const subcategory = `${division} ${category} ${['Zephyr', 'Equilibrium', 'Summit', 'Varied', 'Pro'][Math.floor(Math.random() * 5)]}`;
    const segment = `SEG-${String(500000 + i).padStart(6, '0')} ${subcategory}`;
    const productNo = `PROD-${String(100000 + i).padStart(6, '0')}`;
    const store = stores[Math.floor(Math.random() * stores.length)];

    const totalQty = Math.max(0, Math.round(Math.random() * 200 * Math.exp(-i / 500)));
    const consistency = Math.max(0.05, Math.min(0.95, 0.9 - Math.random() * 0.85 + (totalQty > 50 ? 0.3 : 0)));
    const avgMonthly = totalQty / 11;
    const avgPrice = 30 + Math.random() * 150;
    const promoDependency = Math.random() * 0.5;

    products.push({
      product_no: productNo,
      product_description: subcategory,
      product_division: division,
      product_category: category,
      product_subcategory: subcategory,
      product_segment: segment,
      store,
      total_qty: totalQty,
      avg_monthly: avgMonthly,
      consistency_score: consistency,
      total_revenue: Math.round(totalQty * avgPrice),
      avg_price: avgPrice,
      promo_dependency: promoDependency,
      stockout_risk: Math.max(0, Math.min(1, 0.3 - consistency * 0.2 + Math.random() * 0.3)),
      recommendation: actions[Math.floor(Math.random() * actions.length)],
    });
  }

  return { products };
}
