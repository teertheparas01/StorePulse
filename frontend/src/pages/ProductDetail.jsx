import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ChevronLeft,
  TrendingUp,
  TrendingDown,
  Package,
  AlertTriangle,
  ExternalLink,
  Loader2,
  RefreshCw,
  Tag,
  DollarSign,
  Calendar,
  Warehouse,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { format, formatDistanceToNow, subMonths } from 'date-fns';
import { getDashboardData } from '../services/api';
import './ProductDetail.css';

export default function ProductDetail() {
  const { store, productNo } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [history, setHistory] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [alternatives, setAlternatives] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchData = async () => {
    try {
      setLoading(true);
      // In production, these would be dedicated API calls
      // For now, generate mock data based on the product
      const mockData = generateMockProductData(store, productNo);
      setProduct(mockData.product);
      setHistory(mockData.history);
      setForecast(mockData.forecast);
      setRecommendation(mockData.recommendation);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlternatives = async () => {
    if (!product) return;
    try {
      // In production: const response = await getProductAlternatives(product, 5);
      setAlternatives(generateMockAlternatives(product));
    } catch (err) {
      console.error('Failed to fetch alternatives:', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, [store, productNo]);

  useEffect(() => {
    if (activeTab === 'alternatives' && !alternatives) {
      fetchAlternatives();
    }
  }, [activeTab, alternatives, product]);

  if (loading) {
    return (
      <div className="detail-loading">
        <Loader2 size={48} className="spinner" />
        <p>Loading product details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="detail-error">
        <AlertTriangle size={48} color="var(--danger)" />
        <h2>Failed to load product</h2>
        <p>{error}</p>
        <button className="btn" onClick={fetchData}>
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="detail-error">
        <Package size={48} color="var(--text-muted)" />
        <h2>Product not found</h2>
        <Link to="/catalog" className="btn btn-secondary">
          <ChevronLeft size={16} /> Back to Catalog
        </Link>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Package },
    { id: 'history', label: 'Sales History', icon: TrendingUp },
    { id: 'forecast', label: 'Forecast', icon: ArrowUpRight },
    { id: 'recommendation', label: 'Recommendation', icon: AlertTriangle },
    { id: 'alternatives', label: 'Alternatives', icon: ExternalLink },
  ];

  return (
    <div className="product-detail">
      <div className="detail-header">
        <Link to="/catalog" className="back-link">
          <ChevronLeft size={20} /> Back to Catalog
        </Link>
        <div className="detail-title">
          <h1>{product.product_description}</h1>
          <div className="detail-meta">
            <span className="meta-item"><code>{product.product_no}</code></span>
            <span className="meta-item"><Tag size={14} /> {product.product_segment}</span>
            <span className="meta-item"><Warehouse size={14} /> Store: {product.store}</span>
          </div>
        </div>
        <div className="detail-badges">
          <span className={`badge ${getStatusBadgeClass(product.stock_status)}`}>
            {product.stock_status}
          </span>
          <span className="badge badge-info">{product.product_division}</span>
          <span className="badge badge-neutral">{product.product_category}</span>
        </div>
      </div>

      <div className="tabs-nav" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <tab.icon size={16} />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="tab-content" role="tabpanel">
        {activeTab === 'overview' && <OverviewTab product={product} />}
        {activeTab === 'history' && <HistoryTab history={history} product={product} />}
        {activeTab === 'forecast' && <ForecastTab forecast={forecast} product={product} />}
        {activeTab === 'recommendation' && <RecommendationTab recommendation={recommendation} product={product} />}
        {activeTab === 'alternatives' && <AlternativesTab alternatives={alternatives} product={product} onRefresh={fetchAlternatives} />}
      </div>
    </div>
  );
}

function OverviewTab({ product }) {
  return (
    <div className="tab-panel">
      <div className="kpi-row">
        <KpiCard label="Total Sales (30d)" value={product.total_qty_30d.toLocaleString()} icon={TrendingUp} />
        <KpiCard label="Avg Monthly Qty" value={product.avg_monthly_qty.toFixed(1)} icon={TrendingUp} />
        <KpiCard label="Consistency Score" value={`${(product.consistency_score * 100).toFixed(0)}%`} icon={TrendingUp} />
        <KpiCard label="Revenue (30d)" value={`$${product.revenue_30d.toLocaleString()}`} icon={DollarSign} />
        <KpiCard label="On Hand Inventory" value={product.qty_on_hand.toLocaleString()} icon={Warehouse} />
        <KpiCard label="Weeks of Supply" value={product.weeks_of_supply?.toFixed(1) ?? 'N/A'} icon={Calendar} />
      </div>

      <div className="info-grid">
        <InfoCard title="Product Details">
          <dl>
            <dt>Product No</dt><dd><code>{product.product_no}</code></dd>
            <dt>Division</dt><dd>{product.product_division}</dd>
            <dt>Category</dt><dd>{product.product_category}</dd>
            <dt>Subcategory</dt><dd>{product.product_subcategory}</dd>
            <dt>Segment</dt><dd>{product.product_segment}</dd>
            <dt>Supplier</dt><dd>{product.supplier}</dd>
            <dt>Store</dt><dd>{product.store}</dd>
          </dl>
        </InfoCard>

        <InfoCard title="Current Inventory">
          <dl>
            <dt>Qty on Hand</dt><dd><strong>{product.qty_on_hand.toLocaleString()}</strong></dd>
            <dt>Stock Status</dt><dd><span className={`badge ${getStatusBadgeClass(product.stock_status)}`}>{product.stock_status}</span></dd>
            <dt>Unit Selling Price</dt><dd>${product.unit_selling_price?.toFixed(2) ?? 'N/A'}</dd>
            <dt>Unit Cost Price</dt><dd>${product.unit_cost_price?.toFixed(2) ?? 'N/A'}</dd>
            <dt>Weeks of Supply</dt><dd>{product.weeks_of_supply?.toFixed(1) ?? 'N/A'}</dd>
            <dt>Gap Days Since Obs</dt><dd>{product.gap_days_since_obs ?? 'N/A'}</dd>
            <dt>Negative Qty Flag</dt><dd>{product.negative_qty_flag ? 'Yes' : 'No'}</dd>
            <dt>Writeoff Flag</dt><dd>{product.writeoff_flag ? 'Yes' : 'No'}</dd>
          </dl>
        </InfoCard>

        <InfoCard title="Sales Performance (Last 11 Months)">
          <dl>
            <dt>Total Units Sold</dt><dd><strong>{product.total_qty_all.toLocaleString()}</strong></dd>
            <dt>Total Revenue</dt><dd><strong>${product.total_revenue_all.toLocaleString()}</strong></dd>
            <dt>Avg Monthly Units</dt><dd>{product.avg_monthly_qty.toFixed(1)}</dd>
            <dt>Months with Sales</dt><dd>{product.months_with_sales} / 11</dd>
            <dt>Best Month</dt><dd>{product.best_month_qty} units ({product.best_month})</dd>
            <dt>Consistency Score</dt><dd>{(product.consistency_score * 100).toFixed(0)}%</dd>
            <dt>Zero-Sale Months</dt><dd>{product.zero_sale_months}</dd>
            <dt>Promo Dependency</dt><dd>{(product.promo_dependency * 100).toFixed(0)}%</dd>
          </dl>
        </InfoCard>
      </div>
    </div>
  );
}

function HistoryTab({ history, product }) {
  return (
    <div className="tab-panel">
      <div className="chart-placeholder">
        <div className="chart-title">
          <h3>Monthly Sales Trend</h3>
          <p className="muted">Net quantity sold per month</p>
        </div>
        <MonthlyChart data={history} />
      </div>

      <div className="table-wrapper" style={{ marginTop: 24 }}>
        <table>
          <thead>
            <tr>
              <th>Month</th>
              <th className="numeric">Qty Sold</th>
              <th className="numeric">Revenue</th>
              <th className="numeric">Transactions</th>
              <th className="numeric">Avg Price</th>
              <th>Promo Days</th>
              <th>Markdown Days</th>
            </tr>
          </thead>
          <tbody>
            {history.slice().reverse().map((month) => (
              <tr key={month.month}>
                <td>{format(new Date(month.month + '-01'), 'MMM yyyy')}</td>
                <td className="numeric">{month.qty.toLocaleString()}</td>
                <td className="numeric">${month.revenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                <td className="numeric">{month.transactions.toLocaleString()}</td>
                <td className="numeric">${month.avg_price.toFixed(2)}</td>
                <td>{month.promo_days}</td>
                <td>{month.markdown_days}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ForecastTab({ forecast, product }) {
  if (!forecast) {
    return (
      <div className="empty-state">
        <TrendingUp size={48} color="var(--text-muted)" />
        <h3>No forecast data available</h3>
        <p className="muted">Run the prediction pipeline to generate forecasts for this product.</p>
      </div>
    );
  }

  return (
    <div className="tab-panel">
      <div className="forecast-cards">
        <ForecastCard
          label="Demand Probability"
          value={`${(forecast.demand_probability * 100).toFixed(0)}%`}
          icon={TrendingUp}
          trend={forecast.demand_probability > 0.5 ? 'up' : 'down'}
        />
        <ForecastCard
          label="P10 (Conservative)"
          value={forecast.quantile_10.toFixed(1)}
          icon={ArrowDownRight}
        />
        <ForecastCard
          label="P50 (Expected)"
          value={forecast.quantile_50.toFixed(1)}
          icon={TrendingUp}
        />
        <ForecastCard
          label="P90 (Aggressive)"
          value={forecast.quantile_90.toFixed(1)}
          icon={ArrowUpRight}
        />
      </div>

      <div className="forecast-explanation">
        <h3>How to Interpret</h3>
        <ul>
          <li><strong>Demand Probability:</strong> Model&apos;s confidence that demand {" > "} 0 in the next 7 days</li>
          <li><strong>P10:</strong> Conservative estimate — 90% chance actual demand exceeds this</li>
          <li><strong>P50:</strong> Median estimate — 50% chance actual demand exceeds this</li>
          <li><strong>P90:</strong> Aggressive estimate — 10% chance actual demand exceeds this</li>
          <li><strong>Hurdle Predictions:</strong> Combine probability with quantity (binary × conditional)</li>
        </ul>
      </div>

      <div className="forecast-raw">
        <h3>Raw Prediction Values</h3>
        <dl>
          <dt>demand_probability</dt><dd>{forecast.demand_probability.toFixed(4)}</dd>
          <dt>demand_binary</dt><dd>{forecast.demand_binary}</dd>
          <dt>quantile_10</dt><dd>{forecast.quantile_10.toFixed(4)}</dd>
          <dt>quantile_50</dt><dd>{forecast.quantile_50.toFixed(4)}</dd>
          <dt>quantile_90</dt><dd>{forecast.quantile_90.toFixed(4)}</dd>
          <dt>hurdle_10</dt><dd>{forecast.hurdle_10.toFixed(4)}</dd>
          <dt>hurdle_50</dt><dd>{forecast.hurdle_50.toFixed(4)}</dd>
          <dt>hurdle_90</dt><dd>{forecast.hurdle_90.toFixed(4)}</dd>
        </dl>
      </div>
    </div>
  );
}

function RecommendationTab({ recommendation, product }) {
  if (!recommendation) {
    return (
      <div className="empty-state">
        <AlertTriangle size={48} color="var(--text-muted)" />
        <h3>No recommendation available</h3>
        <p className="muted">Generate recommendations via the inventory actions pipeline.</p>
      </div>
    );
  }

  const actionColors = {
    reorder: 'var(--success)',
    markdown: 'var(--warning)',
    monitor: 'var(--accent-2)',
    hold: 'var(--text-muted)',
  };

  const actionIcons = {
    reorder: TrendingUp,
    markdown: TrendingDown,
    monitor: AlertTriangle,
    hold: Package,
  };

  const ActionIcon = actionIcons[recommendation.action] || Package;

  return (
    <div className="tab-panel">
      <div className="recommendation-card" style={{ '--action-color': actionColors[recommendation.action] }}>
        <div className="rec-header">
          <div className="rec-action">
            <ActionIcon size={32} style={{ color: 'var(--action-color)' }} />
            <div>
              <span className="rec-label">Recommended Action</span>
              <h2 className="rec-action-name">{recommendation.action.toUpperCase()}</h2>
            </div>
          </div>
          <div className="rec-priority">
            <span className={`priority-badge priority-${recommendation.priority}`}>
              {recommendation.priority.toUpperCase()} PRIORITY
            </span>
          </div>
        </div>

        <div className="rec-metrics">
          <div className="rec-metric">
            <span className="rec-metric-label">Order Quantity</span>
            <span className="rec-metric-value">{recommendation.order_qty.toLocaleString()}</span>
          </div>
          <div className="rec-metric">
            <span className="rec-metric-label">Confidence</span>
            <span className="rec-metric-value">{(recommendation.confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="rec-metric">
            <span className="rec-metric-label">Current Inventory</span>
            <span className="rec-metric-value">{product.qty_on_hand.toLocaleString()}</span>
          </div>
        </div>

        <div className="rec-rationale">
          <h3>Rationale</h3>
          <ul>
            {recommendation.rationale.map((reason, idx) => (
              <li key={idx}>{reason}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function AlternativesTab({ alternatives, product, onRefresh }) {
  const [loading, setLoading] = useState(false);

  const handleRefresh = async () => {
    setLoading(true);
    await onRefresh();
    setLoading(false);
  };

  return (
    <div className="tab-panel">
      <div className="alternatives-header">
        <h3>Product Alternatives</h3>
        <button className="btn btn-secondary" onClick={handleRefresh} disabled={loading}>
          <RefreshCw size={16} /> {loading ? 'Searching...' : 'Refresh Search'}
        </button>
      </div>

      {alternatives && alternatives.alternatives?.length > 0 ? (
        <div className="alternatives-list">
          {alternatives.alternatives.map((item, idx) => (
            <div key={idx} className="alternative-card">
              <div className="alt-main">
                <a href={item.url} target="_blank" rel="noreferrer" className="alt-title">
                  {item.title}
                  <ExternalLink size={14} />
                </a>
                <div className="alt-meta">
                  <span className="badge badge-info">{Math.round(item.value_quality_score * 100)}% value/quality</span>
                  {item.rating && <span className="badge badge-neutral">{item.rating}/5 ⭐</span>}
                  {item.price && <span className="badge badge-success">${item.price.toFixed(2)}</span>}
                  <span className="badge badge-neutral">{item.source}</span>
                </div>
              </div>
              <p className="alt-snippet">{item.snippet}</p>
              <div className="alt-evidence">
                <strong>Evidence:</strong>
                <ul>
                  {item.evidence.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              </div>
            </div>
          ))}
        </div>
      ) : alternatives ? (
        <div className="empty-state">
          <ExternalLink size={48} color="var(--text-muted)" />
          <h3>No alternatives found</h3>
          <p className="muted">Try adjusting the search terms or check if the web search API is configured.</p>
        </div>
      ) : (
        <div className="empty-state">
          <ExternalLink size={48} color="var(--text-muted)" />
          <h3>Search for alternatives</h3>
          <p className="muted">Click refresh to search the web for comparable products.</p>
        </div>
      )}
    </div>
  );
}

// Helper components
function KpiCard({ label, value, icon: Icon }) {
  return (
    <div className="kpi-card">
      <div className="kpi-icon"><Icon size={20} /></div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}

function InfoCard({ title, children }) {
  return (
    <div className="info-card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function ForecastCard({ label, value, icon: Icon, trend }) {
  return (
    <div className="forecast-card">
      <div className="fc-icon"><Icon size={20} /></div>
      <div className="fc-label">{label}</div>
      <div className="fc-value">{value}</div>
      {trend && <div className={`fc-trend ${trend}`}>{trend === 'up' ? '▲' : '▼'}</div>}
    </div>
  );
}

function MonthlyChart({ data }) {
  // Simple SVG bar chart
  const maxQty = Math.max(...data.map(d => d.qty), 1);
  const barHeight = 200;

  return (
    <svg width="100%" height={barHeight + 40} className="monthly-chart" viewBox="0 0 800 240">
      {data.map((month, idx) => {
        const x = 40 + idx * 70;
        const barH = (month.qty / maxQty) * barHeight;
        const y = 20 + barHeight - barH;
        return (
          <g key={month.month} style={{ cursor: 'pointer' }}>
            <rect x={x} y={y} width={50} height={barH} fill="var(--accent)" rx={2} opacity="0.8" />
            <text x={x + 25} y={20 + barHeight + 20} textAnchor="middle" fontSize="10" fill="var(--text-muted)">
              {format(new Date(month.month + '-01'), 'MMM')}
            </text>
            <text x={x + 25} y={y - 4} textAnchor="middle" fontSize="11" fill="var(--text)">
              {month.qty > 0 ? month.qty : ''}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function getStatusBadgeClass(status) {
  switch (status?.toLowerCase()) {
    case 'full price': return 'badge-success';
    case 'promo': return 'badge-info';
    case 'markdown tier 1':
    case 'markdown tier 2': return 'badge-warning';
    case 'clearance': return 'badge-danger';
    default: return 'badge-neutral';
  }
}

// Mock data generators
function generateMockProductData(store, productNo) {
  const divisions = ['Scholar Footwear', 'Femme Footwear', 'Junior Apparel'];
  const division = divisions[Math.floor(Math.random() * divisions.length)];
  const categories = {
    'Scholar Footwear': ['Trailblazer', 'Flight Classic', 'Boot Collection', 'Court Casual'],
    'Femme Footwear': ['Trailblazer', 'Flight Classic', 'Court Casual', 'Boot Collection'],
    'Junior Apparel': ['Crop Pants', 'Printed Tees', 'Denim Classics', 'Cozy Pullovers'],
  };
  const category = categories[division][Math.floor(Math.random() * categories[division].length)];
  const subcategory = `${division} ${category} ${['Zephyr', 'Equilibrium', 'Summit', 'Varied'][Math.floor(Math.random() * 4)]}`;
  const segment = `SEG-${String(500000 + Math.floor(Math.random() * 100000)).padStart(6, '0')} ${subcategory}`;

  const totalQty = Math.max(1, Math.round(Math.random() * 200));
  const avgMonthly = totalQty / 11;
  const consistency = Math.max(0.1, Math.min(0.95, 0.9 - Math.random() * 0.8 + (totalQty > 50 ? 0.3 : 0)));

  const product = {
    store,
    product_no: productNo,
    product_description: subcategory,
    product_division: division,
    product_category: category,
    product_subcategory: subcategory,
    product_segment: segment,
    supplier: `Vendor ${String(Math.floor(Math.random() * 30) + 1).padStart(4, '0')}`,
    stock_status: ['Full Price', 'Promo', 'Markdown Tier 1', 'Markdown Tier 2', 'Clearance'][Math.floor(Math.random() * 5)],
    qty_on_hand: Math.max(0, Math.round(Math.random() * 50)),
    unit_selling_price: Math.round(50 + Math.random() * 150),
    unit_cost_price: Math.round(20 + Math.random() * 80),
    weeks_of_supply: Math.random() > 0.3 ? (Math.random() * 12).toFixed(1) : null,
    gap_days_since_obs: Math.floor(Math.random() * 30),
    negative_qty_flag: Math.random() < 0.05,
    writeoff_flag: Math.random() < 0.02,
    total_qty_30d: Math.max(0, Math.round(Math.random() * 20)),
    total_qty_all: totalQty,
    total_revenue_all: Math.round(totalQty * (50 + Math.random() * 150)),
    avg_monthly_qty: avgMonthly,
    consistency_score: consistency,
    months_with_sales: Math.max(1, Math.floor(11 * consistency)),
    best_month_qty: Math.max(1, Math.round(totalQty * 0.3)),
    best_month: format(subMonths(new Date(), Math.floor(Math.random() * 11)), 'MMM yyyy'),
    zero_sale_months: Math.floor((1 - consistency) * 11),
    promo_dependency: Math.random() * 0.4,
    revenue_30d: Math.round(Math.random() * 5000),
  };

  const history = Array.from({ length: 11 }, (_, i) => {
    const date = subMonths(new Date(), 10 - i);
    const baseQty = Math.max(0, Math.round(avgMonthly * (0.5 + Math.random())));
    return {
      month: format(date, 'yyyy-MM'),
      qty: baseQty,
      revenue: Math.round(baseQty * (50 + Math.random() * 100)),
      transactions: baseQty,
      avg_price: 50 + Math.random() * 100,
      promo_days: Math.floor(Math.random() * 5),
      markdown_days: Math.floor(Math.random() * 3),
    };
  });

  const forecast = {
    demand_probability: 0.3 + Math.random() * 0.6,
    demand_binary: Math.random() > 0.5 ? 1 : 0,
    quantile_10: Math.max(0, avgMonthly * (0.3 + Math.random() * 0.4)),
    quantile_50: Math.max(0, avgMonthly * (0.8 + Math.random() * 0.4)),
    quantile_90: Math.max(0, avgMonthly * (1.2 + Math.random() * 0.8)),
    hurdle_10: Math.random() > 0.5 ? Math.max(0, avgMonthly * 0.3) : 0,
    hurdle_50: Math.random() > 0.5 ? Math.max(0, avgMonthly * 0.8) : 0,
    hurdle_90: Math.random() > 0.5 ? Math.max(0, avgMonthly * 1.5) : 0,
  };

  const actions = ['reorder', 'markdown', 'monitor', 'hold'];
  const action = actions[Math.floor(Math.random() * actions.length)];
  const priorities = ['high', 'medium', 'low'];
  const priority = priorities[Math.floor(Math.random() * priorities.length)];

  const rationale = [
    `Predicted demand probability is ${(forecast.demand_probability * 100).toFixed(0)}%.`,
    `Forecast demand is ${forecast.quantile_50.toFixed(1)} units (P50) to ${forecast.quantile_90.toFixed(1)} units (P90).`,
    `Current inventory is ${product.qty_on_hand.toLocaleString()} units.`,
  ];

  if (action === 'reorder') {
    rationale.push('Inventory is below the expected demand range; replenish toward P90.');
  } else if (action === 'markdown') {
    rationale.push('Inventory materially exceeds forecast demand; reduce excess stock.');
  } else if (action === 'monitor') {
    rationale.push('Demand is likely and inventory covers the forecast; monitor sell-through.');
  } else {
    rationale.push('Demand signal is weak and no immediate inventory action is indicated.');
  }

  const recommendation = {
    action,
    priority,
    order_qty: action === 'reorder' ? Math.max(1, Math.round(forecast.quantile_90 - product.qty_on_hand)) : 0,
    confidence: forecast.demand_probability,
    rationale,
  };

  return { product, history, forecast, recommendation };
}

function generateMockAlternatives(product) {
  const alternatives = [
    {
      title: `${product.product_description} Pro`,
      url: 'https://example.com/pro',
      snippet: 'Enhanced version with better durability and comfort. 4.8/5 stars, $120, in stock.',
      source: 'example.com',
      similarity_score: 0.85,
      value_quality_score: 0.82,
      price: 120,
      rating: 4.8,
      evidence: ['85% text similarity to the selected product.', 'Web result reports a 4.8/5 rating.', 'Web result reports a price of 120.00.', 'Availability language was found in the result.'],
    },
    {
      title: `Competitor ${product.product_category} Alternative`,
      url: 'https://competitor.com/alt',
      snippet: 'Similar category product with competitive pricing. 4.5/5 stars, $95, limited stock.',
      source: 'competitor.com',
      similarity_score: 0.72,
      value_quality_score: 0.78,
      price: 95,
      rating: 4.5,
      evidence: ['72% text similarity to the selected product.', 'Web result reports a 4.5/5 rating.', 'Web result reports a price of 95.00.'],
    },
    {
      title: `Budget ${product.product_category} Option`,
      url: 'https://budget.com/option',
      snippet: 'Lower cost alternative with good reviews. 4.2/5 stars, $65, in stock.',
      source: 'budget.com',
      similarity_score: 0.58,
      value_quality_score: 0.75,
      price: 65,
      rating: 4.2,
      evidence: ['58% text similarity to the selected product.', 'Web result reports a 4.2/5 rating.', 'Web result reports a price of 65.00.', 'Availability language was found in the result.'],
    },
  ];
  return { product: { product_no: product.product_no, product_description: product.product_description }, alternatives };
}
