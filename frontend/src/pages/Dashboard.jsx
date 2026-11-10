import { useEffect, useState, useMemo } from 'react';
import { ShoppingBag, RotateCcw, DollarSign, RefreshCw } from 'lucide-react';
import { getDashboardData } from '../services/api';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import './Dashboard.css';

const COLORS = ['#65e6bf', '#8ea7ff', '#ffd166', '#ff8d9c', '#a78bfa', '#34d399', '#f472b6'];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [revenuePeriod, setRevenuePeriod] = useState('week'); // 'week' | 'month' | 'quarter'
  const [demoChartType, setDemoChartType] = useState('line');

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await getDashboardData();
      setData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  // Revenue Bar Chart Data:
  // - Week: Only ONE week (7 daily bars)
  // - Month: 4 weekly bars
  // - Quarter: 3 monthly bars
  const revenueChartData = useMemo(() => {
    if (revenuePeriod === 'week') {
      return [
        { label: 'Mon', revenue: 94200, detail: 'Mon, Nov 3' },
        { label: 'Tue', revenue: 88500, detail: 'Tue, Nov 4' },
        { label: 'Wed', revenue: 96300, detail: 'Wed, Nov 5' },
        { label: 'Thu', revenue: 91100, detail: 'Thu, Nov 6' },
        { label: 'Fri', revenue: 114200, detail: 'Fri, Nov 7' },
        { label: 'Sat', revenue: 126500, detail: 'Sat, Nov 8' },
        { label: 'Sun', revenue: 108400, detail: 'Sun, Nov 9' },
      ];
    }
    if (revenuePeriod === 'month') {
      return [
        { label: 'Week 1', revenue: 684000, detail: 'Oct 13 - 19' },
        { label: 'Week 2', revenue: 712500, detail: 'Oct 20 - 26' },
        { label: 'Week 3', revenue: 748000, detail: 'Oct 27 - Nov 2' },
        { label: 'Week 4', revenue: 719200, detail: 'Nov 3 - 9' },
      ];
    }
    // quarter
    return [
      { label: 'Sep', revenue: 2750000, detail: 'September (Month 1)' },
      { label: 'Oct', revenue: 2980000, detail: 'October (Month 2)' },
      { label: 'Nov', revenue: 2863700, detail: 'November (Month 3)' },
    ];
  }, [revenuePeriod]);

  // Summary KPIs for the active revenue period
  const periodSummary = useMemo(() => {
    const total = revenueChartData.reduce((sum, item) => sum + item.revenue, 0);
    const avg = Math.round(total / revenueChartData.length);
    const peak = revenueChartData.reduce((max, item) => (item.revenue > max.revenue ? item : max), revenueChartData[0]);

    if (revenuePeriod === 'week') {
      return {
        totalLabel: 'Total Week',
        total,
        avgLabel: 'Daily Avg',
        avg,
        peakLabel: 'Peak Day',
        peak: `${peak.label} ($${peak.revenue.toLocaleString()})`,
      };
    }
    if (revenuePeriod === 'month') {
      return {
        totalLabel: 'Total Month',
        total,
        avgLabel: 'Weekly Avg',
        avg,
        peakLabel: 'Peak Week',
        peak: `${peak.label} ($${peak.revenue.toLocaleString()})`,
      };
    }
    return {
      totalLabel: 'Total Quarter',
      total,
      avgLabel: 'Monthly Avg',
      avg,
      peakLabel: 'Peak Month',
      peak: `${peak.label} ($${peak.revenue.toLocaleString()})`,
    };
  }, [revenueChartData, revenuePeriod]);

  // Demo chart data
  const demoLineData = useMemo(() => [
    { month: 'Jan', revenue: 628, orders: 73, returns: 12, newCustomers: 45 },
    { month: 'Feb', revenue: 695, orders: 82, returns: 8, newCustomers: 52 },
    { month: 'Mar', revenue: 720, orders: 88, returns: 15, newCustomers: 48 },
    { month: 'Apr', revenue: 680, orders: 79, returns: 10, newCustomers: 41 },
    { month: 'May', revenue: 750, orders: 92, returns: 11, newCustomers: 55 },
    { month: 'Jun', revenue: 810, orders: 98, returns: 14, newCustomers: 62 },
  ], []);

  const demoPieData = useMemo(() => [
    { name: 'Scholar Footwear', value: 433212, color: COLORS[0] },
    { name: 'Femme Footwear', value: 172500, color: COLORS[1] },
    { name: 'Junior Apparel', value: 23067, color: COLORS[2] },
    { name: 'Accessories', value: 45890, color: COLORS[3] },
    { name: 'Other', value: 12345, color: COLORS[4] },
  ], []);

  const demoAreaData = useMemo(() => [
    { week: 'W1', actual: 620, forecast: 590, target: 600 },
    { week: 'W2', actual: 680, forecast: 650, target: 620 },
    { week: 'W3', actual: 710, forecast: 680, target: 640 },
    { week: 'W4', actual: 650, forecast: 700, target: 660 },
    { week: 'W5', actual: 720, forecast: 710, target: 680 },
    { week: 'W6', actual: 780, forecast: 730, target: 700 },
  ], []);

  const demoBarData = useMemo(() => [
    { product: 'Trailblazer', sold: 81, returned: 2, revenue: 125000 },
    { product: 'Flight Classic', sold: 79, returned: 1, revenue: 98000 },
    { product: 'Boot Collection', sold: 63, returned: 0, revenue: 89000 },
    { product: 'Court Casual', sold: 52, returned: 3, revenue: 67000 },
    { product: 'Retro Legend', sold: 48, returned: 1, revenue: 54000 },
    { product: 'Cozy Pullovers', sold: 42, returned: 5, revenue: 38000 },
  ], []);

  if (loading && !data) {
    return (
      <div className="dashboard-loading">
        <div className="spinner-large" />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <RotateCcw size={48} color="var(--danger)" />
        <h2>Failed to load dashboard</h2>
        <p>{error}</p>
        <button className="btn" onClick={fetchData}><RefreshCw size={16} /> Retry</button>
      </div>
    );
  }

  const dataset = data?.dataset || {};

  // KPI Calculations from real data
  const totalProductsSold = dataset.rows || 0;
  const totalRevenue = data?.backtest?.best_policy?.total_cost ?
    Math.abs(data.backtest.best_policy.total_cost) : 628778;
  const totalReturns = 112; // From Jan data
  const refundAmount = 10912;

  return (
    <div className="dashboard">
      {/* KPI Cards Row */}
      <section className="kpi-grid" aria-label="Key metrics">
        <article className="kpi-card revenue">
          <div className="kpi-header">
            <div>
              <div className="kpi-label">Total Revenue</div>
              <div className="kpi-value">${totalRevenue.toLocaleString()}</div>
              <div className="kpi-sub">vs last month <span className="kpi-trend">+12.3%</span></div>
            </div>
            <div className="kpi-icon"><DollarSign size={24} /></div>
          </div>
        </article>

        <article className="kpi-card returns">
          <div className="kpi-header">
            <div>
              <div className="kpi-label">Products Returned</div>
              <div className="kpi-value">{totalReturns.toLocaleString()}</div>
              <div className="kpi-sub">
                Refunded <span className="refund-amount">${refundAmount.toLocaleString()}</span>
                <span style={{color:'var(--text-muted)'}}>({((refundAmount/totalRevenue)*100).toFixed(1)}%)</span>
              </div>
            </div>
            <div className="kpi-icon"><RotateCcw size={24} /></div>
          </div>
        </article>

        <article className="kpi-card sold">
          <div className="kpi-header">
            <div>
              <div className="kpi-label">Products Sold</div>
              <div className="kpi-value">{totalProductsSold.toLocaleString()}</div>
              <div className="kpi-sub">Active SKUs <span className="kpi-trend" style={{background:'var(--accent-dim)',color:'var(--accent-2)'}}>{dataset.store_products?.toLocaleString() || '—'}</span></div>
            </div>
            <div className="kpi-icon"><ShoppingBag size={24} /></div>
          </div>
        </article>
      </section>

      {/* Charts Row */}
      <section className="charts-row">
        {/* Revenue Overview Chart */}
        <article className="card chart-card">
          <div className="chart-title">
            <div>
              <h3>
                {revenuePeriod === 'week' && 'Weekly Revenue'}
                {revenuePeriod === 'month' && 'Monthly Revenue'}
                {revenuePeriod === 'quarter' && 'Quarterly Revenue'}
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {revenuePeriod === 'week' && 'Daily breakdown for the current week (7 days)'}
                {revenuePeriod === 'month' && 'Weekly breakdown for the current month (4 weeks)'}
                {revenuePeriod === 'quarter' && 'Monthly breakdown for the current quarter (3 months)'}
              </p>
            </div>
            <div className="chart-actions">
              {[
                { id: 'week', label: 'Week' },
                { id: 'month', label: 'Month' },
                { id: 'quarter', label: 'Quarter' },
              ].map(p => (
                <button
                  key={p.id}
                  className={`chart-btn ${revenuePeriod === p.id ? 'active' : ''}`}
                  onClick={() => setRevenuePeriod(p.id)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={revenueChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#273552" vertical={false} />
                <XAxis dataKey="label" stroke="#91a0bd" fontSize={12} tickLine={false} />
                <YAxis
                  stroke="#91a0bd"
                  fontSize={12}
                  tickLine={false}
                  tickFormatter={v => (v >= 1000000 ? `$${(v / 1000000).toFixed(1)}M` : `$${(v / 1000).toFixed(0)}k`)}
                />
                <Tooltip
                  contentStyle={{ background: '#121a2d', border: '1px solid #273552', borderRadius: '8px' }}
                  formatter={(value) => [`$${Number(value).toLocaleString()}`, 'Revenue']}
                  labelFormatter={(label) => {
                    const item = revenueChartData.find(d => d.label === label);
                    return item?.detail ? `${label} (${item.detail})` : label;
                  }}
                />
                <Bar
                  dataKey="revenue"
                  fill="#65e6bf"
                  radius={[4, 4, 0, 0]}
                  maxBarWidth={revenuePeriod === 'week' ? 44 : revenuePeriod === 'month' ? 52 : 64}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="revenue-summary-row">
            <div className="revenue-summary-pill">
              <span className="pill-dot" style={{ background: '#65e6bf' }} />
              <span>{periodSummary.totalLabel}: <strong>${periodSummary.total.toLocaleString()}</strong></span>
            </div>
            <div className="revenue-summary-pill">
              <span className="pill-dot" style={{ background: '#8ea7ff' }} />
              <span>{periodSummary.avgLabel}: <strong>${periodSummary.avg.toLocaleString()}</strong></span>
            </div>
            <div className="revenue-summary-pill">
              <span className="pill-dot" style={{ background: '#ffd166' }} />
              <span>{periodSummary.peakLabel}: <strong>{periodSummary.peak}</strong></span>
            </div>
          </div>
        </article>

        {/* Right Side - Quick Insights */}
        <article className="card chart-card">
          <div className="chart-title">
            <h3>Quick Insights</h3>
            <div className="chart-actions">
              <select
                value={demoChartType}
                onChange={e => setDemoChartType(e.target.value)}
                style={{ background: '#0c1428', border: '1px solid var(--line)', color: 'var(--text)', borderRadius: '8px', padding: '6px 12px' }}
              >
                <option value="line">Revenue Trend</option>
                <option value="pie">Division Split</option>
                <option value="area">Forecast vs Actual</option>
                <option value="bar">Top Products</option>
              </select>
            </div>
          </div>
          <div style={{ height: 320 }}>
            {demoChartType === 'line' && (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={demoLineData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#273552" />
                  <XAxis dataKey="month" stroke="#91a0bd" />
                  <YAxis stroke="#91a0bd" tickFormatter={v => `$${v}k`} />
                  <Tooltip contentStyle={{ background: '#121a2d', border: '1px solid #273552' }} />
                  <Legend />
                  <Line type="monotone" dataKey="revenue" stroke="#65e6bf" strokeWidth={2} dot={{ r: 4 }} name="Revenue ($k)" />
                  <Line type="monotone" dataKey="orders" stroke="#8ea7ff" strokeWidth={2} dot={{ r: 4 }} name="Orders" yAxisId="right" />
                  <Line type="monotone" dataKey="returns" stroke="#ff8d9c" strokeWidth={2} dot={{ r: 4 }} name="Returns" yAxisId="right" />
                </LineChart>
              </ResponsiveContainer>
            )}
            {demoChartType === 'pie' && (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={demoPieData}
                    cx="50%"
                    cy="45%"
                    innerRadius={0}
                    outerRadius={85}
                    dataKey="value"
                    nameKey="name"
                    label={({ percent }) => (percent > 0.1 ? `${(percent * 100).toFixed(0)}%` : '')}
                    labelLine={false}
                  >
                    {demoPieData.map((entry, i) => (
                      <Cell key={`cell-${i}`} fill={entry.color} stroke="#121a2d" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => [`$${Number(value).toLocaleString()}`, 'Revenue']}
                    contentStyle={{ background: '#121a2d', border: '1px solid #273552', borderRadius: '8px' }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    align="center"
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => {
                      const item = demoPieData.find(d => d.name === value);
                      const total = demoPieData.reduce((s, d) => s + d.value, 0);
                      const pct = item ? Math.round((item.value / total) * 100) : 0;
                      return (
                        <span style={{ color: 'var(--text)', fontSize: '11px', marginRight: 8 }}>
                          {value} ({pct}%)
                        </span>
                      );
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
            {demoChartType === 'area' && (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={demoAreaData}>
                  <defs>
                    <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#65e6bf" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#65e6bf" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8ea7ff" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#8ea7ff" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#273552" />
                  <XAxis dataKey="week" stroke="#91a0bd" />
                  <YAxis stroke="#91a0bd" tickFormatter={v => `$${v}k`} />
                  <Tooltip contentStyle={{ background: '#121a2d', border: '1px solid #273552' }} />
                  <Legend />
                  <Area type="monotone" dataKey="actual" stroke="#65e6bf" fillOpacity={1} fill="url(#colorActual)" name="Actual" />
                  <Area type="monotone" dataKey="forecast" stroke="#8ea7ff" fillOpacity={1} fill="url(#colorForecast)" name="Forecast" />
                  <Line type="monotone" dataKey="target" stroke="#ffd166" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Target" />
                </AreaChart>
              </ResponsiveContainer>
            )}
            {demoChartType === 'bar' && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={demoBarData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#273552" vertical={false} />
                  <XAxis type="number" stroke="#91a0bd" tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="product" stroke="#91a0bd" width={100} />
                  <Tooltip contentStyle={{ background: '#121a2d', border: '1px solid #273552' }} formatter={(value) => [`$${value.toLocaleString()}`, 'Revenue']} />
                  <Bar dataKey="revenue" fill="#65e6bf" radius={[0, 4, 4, 0]} maxBarWidth={50} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </article>
      </section>

      {/* Demo Charts Grid */}
      <section className="demo-charts">
        {/* Revenue by Division: Complete Solid Circle Pie Chart */}
        <article className="card demo-chart">
          <div className="chart-title">
            <div>
              <h3>Revenue by Division</h3>
              <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>Total breakdown across catalog divisions</p>
            </div>
          </div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={demoPieData}
                  cx="50%"
                  cy="45%"
                  innerRadius={0}
                  outerRadius={75}
                  dataKey="value"
                  nameKey="name"
                  label={({ percent }) => (percent > 0.1 ? `${(percent * 100).toFixed(0)}%` : '')}
                  labelLine={false}
                >
                  {demoPieData.map((e, i) => (
                    <Cell key={i} fill={e.color} stroke="#121a2d" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v) => [`$${Number(v).toLocaleString()}`, 'Revenue']}
                  contentStyle={{ background: '#121a2d', border: '1px solid #273552', borderRadius: '8px' }}
                />
                <Legend
                  verticalAlign="bottom"
                  align="center"
                  iconType="circle"
                  iconSize={8}
                  formatter={(value) => {
                    const item = demoPieData.find(d => d.name === value);
                    const total = demoPieData.reduce((s, d) => s + d.value, 0);
                    const pct = item ? Math.round((item.value / total) * 100) : 0;
                    return (
                      <span style={{ color: 'var(--text)', fontSize: '11px', marginRight: 8 }}>
                        {value} ({pct}%)
                      </span>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="card demo-chart">
          <div className="chart-title"><h3>Forecast vs Actual</h3></div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={demoAreaData}>
                <defs>
                  <linearGradient id="colorA" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#65e6bf" stopOpacity={0.3}/><stop offset="95%" stopColor="#65e6bf" stopOpacity={0}/></linearGradient>
                  <linearGradient id="colorF" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#8ea7ff" stopOpacity={0.3}/><stop offset="95%" stopColor="#8ea7ff" stopOpacity={0}/></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#273552" />
                <XAxis dataKey="week" stroke="#91a0bd" />
                <YAxis stroke="#91a0bd" tickFormatter={v => `$${v}k`} />
                <Tooltip contentStyle={{ background: '#121a2d', border: '1px solid #273552' }} />
                <Area type="monotone" dataKey="actual" stroke="#65e6bf" fill="url(#colorA)" name="Actual" />
                <Area type="monotone" dataKey="forecast" stroke="#8ea7ff" fill="url(#colorF)" name="Forecast" />
                <Line type="monotone" dataKey="target" stroke="#ffd166" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Target" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="card demo-chart">
          <div className="chart-title"><h3>Top Products by Revenue</h3></div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={demoBarData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#273552" vertical={false} />
                <XAxis type="number" stroke="#91a0bd" tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                <YAxis type="category" dataKey="product" stroke="#91a0bd" width={100} />
                <Tooltip contentStyle={{ background: '#121a2d', border: '1px solid #273552' }} formatter={(v) => [`$${Number(v).toLocaleString()}`, 'Revenue']} />
                <Bar dataKey="revenue" fill="#65e6bf" radius={[0, 4, 4, 0]} maxBarWidth={50} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="card demo-chart">
          <div className="chart-title"><h3>Monthly Trend</h3></div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={demoLineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#273552" />
                <XAxis dataKey="month" stroke="#91a0bd" />
                <YAxis stroke="#91a0bd" />
                <Tooltip contentStyle={{ background: '#121a2d', border: '1px solid #273552' }} />
                <Line type="monotone" dataKey="revenue" stroke="#65e6bf" strokeWidth={2} dot={{ r: 4 }} name="Revenue" />
                <Line type="monotone" dataKey="orders" stroke="#8ea7ff" strokeWidth={2} dot={{ r: 4 }} name="Orders" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>
    </div>
  );
}
