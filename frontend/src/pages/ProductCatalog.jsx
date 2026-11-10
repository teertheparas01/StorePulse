import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, ChevronDown, Loader2, Package, TrendingUp, AlertTriangle } from 'lucide-react';
import { format } from 'date-fns';
import { getDashboardData } from '../services/api';
import './ProductCatalog.css';

export default function ProductCatalog() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [divisionFilter, setDivisionFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortConfig, setSortConfig] = useState({ key: 'total_qty', direction: 'desc' });
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 50;

  // Simulated data loading - in real app, this would call an API endpoint
  const fetchData = async () => {
    try {
      setLoading(true);
      // For now, we'll use the dashboard data and simulate catalog data
      // In production, this would be a dedicated /catalog endpoint
      const response = await getDashboardData();

      // Generate mock catalog data based on dashboard stats
      const mockData = generateMockCatalogData(response.data);
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

  const filteredData = useMemo(() => {
    return data
      .filter((item) => {
        const matchesSearch = item.product_description.toLowerCase().includes(search.toLowerCase()) ||
          item.product_no.toLowerCase().includes(search.toLowerCase());
        const matchesDivision = divisionFilter === 'all' || item.product_division === divisionFilter;
        const matchesStatus = statusFilter === 'all' || item.stock_status === statusFilter;
        return matchesSearch && matchesDivision && matchesStatus;
      })
      .sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
  }, [data, search, divisionFilter, statusFilter, sortConfig]);

  const paginatedData = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredData.slice(start, start + PAGE_SIZE);
  }, [filteredData, page]);

  const totalPages = Math.ceil(filteredData.length / PAGE_SIZE);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const divisions = useMemo(() => [...new Set(data.map(d => d.product_division))].sort(), [data]);
  const statuses = useMemo(() => [...new Set(data.map(d => d.stock_status))].sort(), [data]);

  if (loading) {
    return (
      <div className="catalog-loading">
        <Loader2 size={48} className="spinner" />
        <p>Loading product catalog...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="catalog-error">
        <AlertTriangle size={48} color="var(--danger)" />
        <h2>Failed to load catalog</h2>
        <p>{error}</p>
        <button className="btn" onClick={fetchData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="catalog">
      <div className="catalog-header">
        <div>
          <h1>Product Catalog</h1>
          <p className="subtitle">{data.length.toLocaleString()} products across {divisions.length} divisions</p>
        </div>
        <div className="header-actions">
          <div className="search-box">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search products..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Division</label>
          <select value={divisionFilter} onChange={(e) => setDivisionFilter(e.target.value)}>
            <option value="all">All Divisions</option>
            {divisions.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Stock Status</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">All Statuses</option>
            {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              {[
                { key: 'product_no', label: 'Product No' },
                { key: 'product_description', label: 'Description' },
                { key: 'product_division', label: 'Division' },
                { key: 'product_category', label: 'Category' },
                { key: 'product_subcategory', label: 'Subcategory' },
                { key: 'total_qty', label: 'Total Qty (30d)', numeric: true },
                { key: 'avg_monthly_qty', label: 'Avg Monthly', numeric: true },
                { key: 'consistency_score', label: 'Consistency', numeric: true },
                { key: 'stock_status', label: 'Stock Status' },
                { key: 'qty_on_hand', label: 'On Hand', numeric: true },
                { key: 'weeks_of_supply', label: 'Weeks Supply', numeric: true },
                { key: 'action', label: 'Action' },
              ].map((col) => (
                <th
                  key={col.key}
                  onClick={() => !col.action && handleSort(col.key)}
                  style={{ cursor: col.action ? 'default' : 'pointer', width: col.width }}
                >
                  <div className="th-content">
                    <span>{col.label}</span>
                    {!col.action && sortConfig.key === col.key && (
                      <ChevronDown size={14} className={sortConfig.direction === 'asc' ? 'asc' : ''} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((item, idx) => (
              <tr key={item.product_no} onClick={() => navigate(`/catalog/detail/${item.store}/${item.product_no}`)}>
                <td><code>{item.product_no}</code></td>
                <td className="description-cell">
                  <span className="desc-main">{item.product_description}</span>
                  <span className="desc-meta">{item.product_segment}</span>
                </td>
                <td>{item.product_division}</td>
                <td>{item.product_category}</td>
                <td>{item.product_subcategory}</td>
                <td className="numeric">{item.total_qty.toLocaleString()}</td>
                <td className="numeric">{item.avg_monthly_qty.toFixed(1)}</td>
                <td className="numeric">
                  <span className={`consistency-badge ${item.consistency_score > 0.7 ? 'high' : item.consistency_score > 0.4 ? 'medium' : 'low'}`}>
                    {(item.consistency_score * 100).toFixed(0)}%
                  </span>
                </td>
                <td>
                  <span className={`badge ${getStatusBadgeClass(item.stock_status)}`}>
                    {item.stock_status}
                  </span>
                </td>
                <td className="numeric">{item.qty_on_hand.toLocaleString()}</td>
                <td className="numeric">{item.weeks_of_supply?.toFixed(1) ?? '—'}</td>
                <td>
                  <button
                    className="btn btn-sm"
                    onClick={(e) => { e.stopPropagation(); navigate(`/catalog/detail/${item.store}/${item.product_no}`); }}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
            {paginatedData.length === 0 && (
              <tr>
                <td colSpan={12} className="empty-row">No products match your filters</td>
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
            Page {page} of {totalPages} ({filteredData.length.toLocaleString()} products)
          </span>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
            Next
          </button>
        </div>
      )}
    </div>
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

// Mock data generator - replace with real API call
function generateMockCatalogData(dashboardData) {
  const products = [];
  const divisions = ['Scholar Footwear', 'Femme Footwear', 'Junior Apparel'];
  const categories = {
    'Scholar Footwear': ['Trailblazer', 'Flight Classic', 'Boot Collection', 'Court Casual', 'Canvas Styles', 'Retro Legend', 'Modern Legend', 'Trainer'],
    'Femme Footwear': ['Trailblazer', 'Flight Classic', 'Court Casual', 'Boot Collection', 'Retro Legend'],
    'Junior Apparel': ['Crop Pants', 'Printed Tees', 'Denim Classics', 'Cozy Pullovers', 'Cozy Trousers', 'Crew Tees', 'Light Shells'],
  };
  const stores = Array.from({ length: 40 }, (_, i) => `STR-${String(1000 + i).padStart(4, '0')}`);
  const statuses = ['Full Price', 'Promo', 'Markdown Tier 1', 'Markdown Tier 2', 'Clearance'];

  for (let i = 0; i < 2326; i++) {
    const division = divisions[i % divisions.length];
    const catList = categories[division];
    const category = catList[i % catList.length];
    const subcategory = `${division} ${category} ${['Zephyr', 'Equilibrium', 'Summit', 'Varied', 'Pro', 'Swift Run', 'Stride Pro'][i % 7]}`;
    const segment = `SEG-${String(500000 + i).padStart(6, '0')} ${subcategory}`;
    const productNo = `PROD-${String(100000 + i).padStart(6, '0')}`;
    const store = stores[i % stores.length];

    const baseQty = Math.max(0, Math.round(Math.random() * 200 * Math.exp(-i / 500)));
    const monthlyQty = baseQty / 11;
    const consistency = Math.max(0, Math.min(1, 0.9 - Math.random() * 0.8 + (baseQty > 50 ? 0.3 : 0)));

    products.push({
      product_no: productNo,
      product_description: subcategory,
      product_division: division,
      product_category: category,
      product_subcategory: subcategory,
      product_segment: segment,
      store,
      total_qty: baseQty,
      avg_monthly_qty: monthlyQty,
      consistency_score: consistency,
      stock_status: statuses[Math.floor(Math.random() * statuses.length)],
      qty_on_hand: Math.max(0, Math.round(Math.random() * 50)),
      weeks_of_supply: Math.random() > 0.3 ? (Math.random() * 12).toFixed(1) : null,
    });
  }

  return products;
}
