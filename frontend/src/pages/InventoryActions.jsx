import { useEffect, useState, useMemo } from 'react';
import { Search, Filter, ChevronDown, Loader2, AlertTriangle, CheckCircle, XCircle, Clock, Download } from 'lucide-react';
import { format } from 'date-fns';
import { getDashboardData } from '../services/api';
import './InventoryActions.css';

export default function InventoryActions() {
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('pending');
  const [sortConfig, setSortConfig] = useState({ key: 'priority_score', direction: 'desc' });
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const PAGE_SIZE = 25;

  const fetchData = async () => {
    try {
      setLoading(true);
      // In production: const response = await getInventoryActions({ status: statusFilter });
      const mockData = generateMockActions();
      setActions(mockData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const filteredActions = useMemo(() => {
    return actions
      .filter((item) => {
        const matchesSearch = item.product_description.toLowerCase().includes(search.toLowerCase()) ||
          item.product_no.toLowerCase().includes(search.toLowerCase()) ||
          item.store.toLowerCase().includes(search.toLowerCase());
        const matchesAction = actionFilter === 'all' || item.action === actionFilter;
        const matchesPriority = priorityFilter === 'all' || item.priority === priorityFilter;
        return matchesSearch && matchesAction && matchesPriority;
      })
      .sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
  }, [actions, search, actionFilter, priorityFilter, sortConfig]);

  const paginatedActions = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredActions.slice(start, start + PAGE_SIZE);
  }, [filteredActions, page]);

  const totalPages = Math.ceil(filteredActions.length / PAGE_SIZE);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === paginatedActions.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(paginatedActions.map(a => a.id)));
    }
  };

  const bulkApprove = async () => {
    const ids = Array.from(selectedIds);
    // In production: await approveActions(ids);
    setActions((prev) => prev.map((a) => (ids.includes(a.id) ? { ...a, status: 'approved', approved_at: new Date().toISOString() } : a)));
    setSelectedIds(new Set());
  };

  const bulkReject = async () => {
    const ids = Array.from(selectedIds);
    // In production: await rejectActions(ids);
    setActions((prev) => prev.map((a) => (ids.includes(a.id) ? { ...a, status: 'rejected', rejected_at: new Date().toISOString() } : a)));
    setSelectedIds(new Set());
  };

  const stats = useMemo(() => ({
    total: actions.length,
    pending: actions.filter(a => a.status === 'pending').length,
    approved: actions.filter(a => a.status === 'approved').length,
    rejected: actions.filter(a => a.status === 'rejected').length,
    highPriority: actions.filter(a => a.priority === 'high' && a.status === 'pending').length,
  }), [actions]);

  if (loading) {
    return (
      <div className="actions-loading">
        <Loader2 size={48} className="spinner" />
        <p>Loading inventory actions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="actions-error">
        <AlertTriangle size={48} color="var(--danger)" />
        <h2>Failed to load actions</h2>
        <p>{error}</p>
        <button className="btn" onClick={fetchData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="inventory-actions">
      <div className="actions-header">
        <div>
          <h1>Inventory Actions</h1>
          <p className="subtitle">Review and approve AI-generated inventory recommendations</p>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" disabled={selectedIds.size === 0}>
            <Download size={16} /> Export Selected
          </button>
        </div>
      </div>

      <div className="stats-bar">
        <StatCard label="Total" value={stats.total} icon="📋" />
        <StatCard label="Pending" value={stats.pending} variant="warning" icon={<Clock size={20} />} />
        <StatCard label="Approved" value={stats.approved} variant="success" icon={<CheckCircle size={20} />} />
        <StatCard label="Rejected" value={stats.rejected} variant="danger" icon={<XCircle size={20} />} />
        <StatCard label="High Priority" value={stats.highPriority} variant="danger" icon={<AlertTriangle size={20} />} />
      </div>

      <div className="filters-bar">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search products, stores..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <label>Action</label>
          <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
            <option value="all">All Actions</option>
            <option value="reorder">Reorder</option>
            <option value="markdown">Markdown</option>
            <option value="monitor">Monitor</option>
            <option value="hold">Hold</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Priority</label>
          <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
            <option value="all">All Priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Status</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="all">All</option>
          </select>
        </div>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th style={{ width: 48 }}>
                <input
                  type="checkbox"
                  checked={selectedIds.size === paginatedActions.length && paginatedActions.length > 0}
                  indeterminate={selectedIds.size > 0 && selectedIds.size < paginatedActions.length}
                  onChange={toggleSelectAll}
                  aria-label="Select all"
                />
              </th>
              {[
                { key: 'product_no', label: 'Product No' },
                { key: 'product_description', label: 'Description' },
                { key: 'store', label: 'Store' },
                { key: 'action', label: 'Action' },
                { key: 'priority', label: 'Priority' },
                { key: 'order_qty', label: 'Order Qty', numeric: true },
                { key: 'confidence', label: 'Confidence', numeric: true },
                { key: 'demand_prob', label: 'Demand Prob', numeric: true },
                { key: 'inventory', label: 'On Hand', numeric: true },
                { key: 'forecast_p50', label: 'P50 Forecast', numeric: true },
                { key: 'forecast_p90', label: 'P90 Forecast', numeric: true },
                { key: 'rationale_preview', label: 'Rationale' },
                { key: 'status', label: 'Status' },
                { key: 'created_at', label: 'Created' },
              ].map((col) => (
                <th
                  key={col.key}
                  onClick={() => !col.action && handleSort(col.key)}
                  style={{ cursor: col.action ? 'default' : 'pointer' }}
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
            {paginatedActions.map((item) => (
              <tr key={item.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.id)}
                    onChange={() => toggleSelect(item.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                </td>
                <td><code>{item.product_no}</code></td>
                <td className="description-cell">
                  <span className="desc-main">{item.product_description}</span>
                  <span className="desc-meta">{item.product_segment}</span>
                </td>
                <td>{item.store}</td>
                <td>
                  <span className={`action-badge action-${item.action}`}>
                    {item.action.toUpperCase()}
                  </span>
                </td>
                <td>
                  <span className={`priority-badge priority-${item.priority}`}>
                    {item.priority.toUpperCase()}
                  </span>
                </td>
                <td className="numeric">{item.order_qty.toLocaleString()}</td>
                <td className="numeric">{(item.confidence * 100).toFixed(0)}%</td>
                <td className="numeric">{(item.demand_prob * 100).toFixed(0)}%</td>
                <td className="numeric">{item.inventory.toLocaleString()}</td>
                <td className="numeric">{item.forecast_p50.toFixed(1)}</td>
                <td className="numeric">{item.forecast_p90.toFixed(1)}</td>
                <td className="rationale-cell">{item.rationale_preview}</td>
                <td>
                  <span className={`status-badge status-${item.status}`}>
                    {item.status === 'pending' && <Clock size={12} />}
                    {item.status === 'approved' && <CheckCircle size={12} />}
                    {item.status === 'rejected' && <XCircle size={12} />}
                    {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                  </span>
                </td>
                <td className="numeric">{format(new Date(item.created_at), 'MMM d, HH:mm')}</td>
              </tr>
            ))}
            {paginatedActions.length === 0 && (
              <tr>
                <td colSpan={15} className="empty-row">No actions match your filters</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedIds.size > 0 && statusFilter === 'pending' && (
        <div className="bulk-actions">
          <span>{selectedIds.size} selected</span>
          <div className="bulk-buttons">
            <button className="btn btn-success" onClick={bulkApprove}>
              <CheckCircle size={16} /> Approve
            </button>
            <button className="btn btn-danger" onClick={bulkReject}>
              <XCircle size={16} /> Reject
            </button>
          </div>
        </div>
      )}

      {totalPages > 1 && (
        <div className="pagination">
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
            Previous
          </button>
          <span className="pagination-info">
            Page {page} of {totalPages} ({filteredActions.length.toLocaleString()} actions)
          </span>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, variant, icon, icon: Icon }) {
  const colors = {
    success: { bg: 'var(--success-dim)', color: 'var(--success)', border: 'var(--success)' },
    warning: { bg: 'var(--warning-dim)', color: 'var(--warning)', border: 'var(--warning)' },
    danger: { bg: 'var(--danger-dim)', color: 'var(--danger)', border: 'var(--danger)' },
    default: { bg: 'var(--accent-dim)', color: 'var(--accent)', border: 'var(--accent)' },
  };
  const c = colors[variant || 'default'];

  return (
    <div className="stat-card" style={{ '--stat-color': c.color, '--stat-bg': c.bg, '--stat-border': c.border }}>
      <div className="stat-icon" style={{ background: c.bg, color: c.color }}>
        {typeof icon === 'string' ? <span style={{ fontSize: 20 }}>{icon}</span> : <Icon />}
      </div>
      <div className="stat-content">
        <div className="stat-value">{value.toLocaleString()}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

// Mock data generator
function generateMockActions() {
  const actions = [];
  const actionTypes = ['reorder', 'markdown', 'monitor', 'hold'];
  const priorities = ['high', 'medium', 'low'];
  const statuses = ['pending', 'approved', 'rejected'];
  const divisions = ['Scholar Footwear', 'Femme Footwear', 'Junior Apparel'];
  const categories = {
    'Scholar Footwear': ['Trailblazer', 'Flight Classic', 'Boot Collection', 'Court Casual'],
    'Femme Footwear': ['Trailblazer', 'Flight Classic', 'Court Casual', 'Boot Collection'],
    'Junior Apparel': ['Crop Pants', 'Printed Tees', 'Denim Classics', 'Cozy Pullovers'],
  };
  const stores = Array.from({ length: 40 }, (_, i) => `STR-${String(1000 + i).padStart(4, '0')}`);

  for (let i = 0; i < 500; i++) {
    const division = divisions[Math.floor(Math.random() * divisions.length)];
    const catList = categories[division];
    const category = catList[Math.floor(Math.random() * catList.length)];
    const subcategory = `${division} ${category} ${['Zephyr', 'Equilibrium', 'Summit', 'Varied'][Math.floor(Math.random() * 4)]}`;
    const segment = `SEG-${String(500000 + i).padStart(6, '0')} ${subcategory}`;
    const productNo = `PROD-${String(100000 + i).padStart(6, '0')}`;
    const store = stores[Math.floor(Math.random() * stores.length)];
    const action = actionTypes[Math.floor(Math.random() * actionTypes.length)];
    const priority = priorities[Math.floor(Math.random() * priorities.length)];
    const status = statuses[Math.floor(Math.random() * statuses.length)];

    const demandProb = 0.2 + Math.random() * 0.7;
    const p50 = Math.max(0, Math.random() * 20);
    const p90 = p50 * (1.5 + Math.random());
    const inventory = Math.max(0, Math.round(Math.random() * 50));
    const orderQty = action === 'reorder' ? Math.max(1, Math.round(p90 - inventory)) : 0;
    const confidence = 0.5 + Math.random() * 0.4;

    let rationale = '';
    if (action === 'reorder') rationale = 'Inventory below expected demand; replenish toward P90.';
    else if (action === 'markdown') rationale = 'Inventory exceeds forecast; reduce excess stock.';
    else if (action === 'monitor') rationale = 'Demand likely and inventory covers forecast; monitor sell-through.';
    else rationale = 'Demand signal weak; no immediate action indicated.';

    actions.push({
      id: `act-${i}`,
      product_no: productNo,
      product_description: subcategory,
      product_segment: segment,
      store,
      action,
      priority,
      status,
      order_qty: orderQty,
      confidence,
      demand_prob: demandProb,
      inventory,
      forecast_p50: p50,
      forecast_p90: p90,
      rationale_preview: rationale.length > 60 ? rationale.slice(0, 60) + '…' : rationale,
      created_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
      priority_score: (priority === 'high' ? 3 : priority === 'medium' ? 2 : 1) * confidence,
    });
  }

  return actions.sort((a, b) => b.priority_score - a.priority_score);
}
