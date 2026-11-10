import { useEffect, useState, useMemo } from 'react';
import { Loader2, AlertTriangle, RefreshCw, TrendingUp, TrendingDown, CheckCircle, XCircle, Clock, BarChart2, ExternalLink } from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { getDashboardData } from '../services/api';
import './ModelMonitoring.css';

export default function ModelMonitoring() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [selectedTab, setSelectedTab] = useState('overview');

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await getDashboardData();
      // In production, also fetch /monitoring for detailed data
      setData(response.data);
      setLastRefreshed(new Date());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 120000); // Every 2 minutes
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart2 },
    { id: 'feature-drift', label: 'Feature Drift', icon: TrendingUp },
    { id: 'prediction-drift', label: 'Prediction Drift', icon: TrendingDown },
    { id: 'performance', label: 'Performance', icon: CheckCircle },
    { id: 'backtest', label: 'Backtest Policies', icon: ExternalLink },
  ];

  const monitoring = data?.monitoring || {};
  const backtest = data?.backtest || {};
  const model = data?.model || {};

  const featureDrift = monitoring?.feature_drift || {};
  const predictionDrift = monitoring?.prediction_drift || {};
  const performance = monitoring?.performance || {};
  const policies = backtest?.policies || [];
  const bestPolicy = backtest?.best_policy;

  const driftedFeatures = monitoring?.drifted_features || [];
  const driftCount = monitoring?.drift_count || 0;

  if (loading && !data) {
    return (
      <div className="monitoring-loading">
        <Loader2 size={48} className="spinner" />
        <p>Loading monitoring data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="monitoring-error">
        <AlertTriangle size={48} color="var(--danger)" />
        <h2>Failed to load monitoring</h2>
        <p>{error}</p>
        <button className="btn" onClick={fetchData}>
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="model-monitoring">
      <div className="monitoring-header">
        <div>
          <h1>Model Monitoring</h1>
          <p className="subtitle">Track feature drift, prediction drift, and model performance over time</p>
        </div>
        <div className="header-controls">
          <div className="status-pill">
            <span className={`status-dot ${driftCount === 0 ? 'healthy' : 'danger'}`}></span>
            <span>
              {driftCount === 0 ? 'All Clear' : `${driftCount} Drift Alert${driftCount > 1 ? 's' : ''}`}
            </span>
          </div>
          <div className="refresh-info">
            <Clock size={14} />
            <span>Last updated: {lastRefreshed ? formatDistanceToNow(lastRefreshed, { addSuffix: true }) : '—'}</span>
            <button className="btn btn-secondary btn-sm" onClick={fetchData}>
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="tabs-nav" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={selectedTab === tab.id}
            className={`tab-btn ${selectedTab === tab.id ? 'active' : ''}`}
            onClick={() => setSelectedTab(tab.id)}
          >
            <tab.icon size={16} />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="tab-content" role="tabpanel">
        {selectedTab === 'overview' && <OverviewTab monitoring={monitoring} backtest={backtest} model={model} />}
        {selectedTab === 'feature-drift' && <FeatureDriftTab featureDrift={featureDrift} />}
        {selectedTab === 'prediction-drift' && <PredictionDriftTab predictionDrift={predictionDrift} />}
        {selectedTab === 'performance' && <PerformanceTab performance={performance} />}
        {selectedTab === 'backtest' && <BacktestTab policies={policies} bestPolicy={bestPolicy} />}
      </div>
    </div>
  );
}

function OverviewTab({ monitoring, backtest, model }) {
  const featureDrift = monitoring?.feature_drift || {};
  const predictionDrift = monitoring?.prediction_drift || {};
  const performance = monitoring?.performance || {};
  const policies = backtest?.policies || [];
  const bestPolicy = backtest?.best_policy;
  const driftCount = monitoring?.drift_count || 0;
  const driftedFeatures = monitoring?.drifted_features || [];

  return (
    <div className="tab-panel">
      <div className="kpi-row">
        <KpiCard label="Feature Drift Alerts" value={driftCount} variant={driftCount === 0 ? 'success' : 'danger'} icon={AlertTriangle} />
        <KpiCard label="Drifted Features" value={driftedFeatures.length} variant="info" icon={TrendingUp} />
        <KpiCard label="Prediction Drift" value={Object.keys(predictionDrift).filter(k => predictionDrift[k]?.drift_detected).length} variant="warning" icon={TrendingDown} />
        <KpiCard label="Performance OK" value={Object.values(performance).every(p => p?.performance_ok) ? 'Yes' : 'No'} variant={Object.values(performance).every(p => p?.performance_ok) ? 'success' : 'danger'} icon={CheckCircle} />
        <KpiCard label="Best Policy" value={bestPolicy?.name || '—'} icon={ExternalLink} />
        <KpiCard label="Policy Cost" value={bestPolicy?.total_cost?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || '—'} icon={TrendingUp} />
      </div>

      <div className="overview-grid">
        <div className="card">
          <h3>Drifted Features</h3>
          <div className="chips">
            {driftedFeatures.length > 0 ? (
              driftedFeatures.slice(0, 15).map((name) => (
                <span key={name} className="chip">{name}</span>
              ))
            ) : (
              <span className="muted">No drift alerts</span>
            )}
          </div>
        </div>

        <div className="card">
          <h3>Model Status</h3>
          <div className="snapshot">
            <div><span>Model</span><strong>{model?.name || 'demand_forecaster'}</strong></div>
            <div><span>Loaded</span><strong>{model?.loaded ? 'Yes' : 'No'}</strong></div>
            <div><span>Features</span><strong>{model?.features || 0}</strong></div>
            <div><span>Quantiles</span><strong>q10, q50, q90</strong></div>
          </div>
        </div>

        <div className="card">
          <h3>Backtest Summary</h3>
          <div className="policy-list">
            {policies.slice(0, 6).map((policy) => (
              <div key={policy.name} className="policy">
                <span>{policy.name}{policy.name === bestPolicy?.name && ' ⭐'}</span>
                <strong>{policy.total_cost?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
              </div>
            ))}
            {policies.length === 0 && <span className="muted">No backtest artifact</span>}
          </div>
        </div>

        <div className="card">
          <h3>Monitoring Timestamp</h3>
          <p className="muted">{monitoring.timestamp ? format(new Date(monitoring.timestamp), 'MMM d, yyyy HH:mm:ss') : 'No data'}</p>
          {monitoring.summary && (
            <div className="summary-flags">
              <div className={`flag ${monitoring.summary.feature_drift_detected ? 'alert' : 'ok'}`}>
                <span>Feature Drift:</span>
                <strong>{monitoring.summary.feature_drift_detected ? 'DETECTED' : 'OK'}</strong>
              </div>
              <div className={`flag ${monitoring.summary.prediction_drift_detected ? 'alert' : 'ok'}`}>
                <span>Prediction Drift:</span>
                <strong>{monitoring.summary.prediction_drift_detected ? 'DETECTED' : 'OK'}</strong>
              </div>
              <div className={`flag ${monitoring.summary.performance_degraded ? 'alert' : 'ok'}`}>
                <span>Performance:</span>
                <strong>{monitoring.summary.performance_degraded ? 'DEGRADED' : 'OK'}</strong>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FeatureDriftTab({ featureDrift }) {
  const driftEntries = useMemo(() => {
    return Object.entries(featureDrift)
      .filter(([k, v]) => k !== '_summary' && v && typeof v === 'object')
      .sort((a, b) => (b[1]?.psi || 0) - (a[1]?.psi || 0));
  }, [featureDrift]);

  if (driftEntries.length === 0) {
    return (
      <div className="empty-state">
        <TrendingUp size={48} color="var(--text-muted)" />
        <h3>No feature drift data</h3>
        <p className="muted">Run the monitoring pipeline to generate drift analysis.</p>
      </div>
    );
  }

  return (
    <div className="tab-panel">
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Feature</th>
              <th className="numeric">PSI</th>
              <th>Drift Detected</th>
              <th className="numeric">Max PSI</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            {driftEntries.map(([feature, info]) => (
              <tr key={feature}>
                <td><code>{feature}</code></td>
                <td className="numeric">{(info.psi || 0).toFixed(4)}</td>
                <td>
                  <span className={`badge ${info.drift_detected ? 'badge-danger' : 'badge-success'}`}>
                    {info.drift_detected ? 'YES' : 'NO'}
                  </span>
                </td>
                <td className="numeric">{(featureDrift._summary?.max_psi || 0).toFixed(4)}</td>
                <td>
                  <span className={`severity-badge severity-${(info.psi || 0) > 0.2 ? 'high' : (info.psi || 0) > 0.1 ? 'medium' : 'low'}`}>
                    {(info.psi || 0) > 0.2 ? 'HIGH' : (info.psi || 0) > 0.1 ? 'MEDIUM' : 'LOW'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PredictionDriftTab({ predictionDrift }) {
  const entries = Object.entries(predictionDrift).filter(([k, v]) => v && typeof v === 'object');

  if (entries.length === 0) {
    return (
      <div className="empty-state">
        <TrendingDown size={48} color="var(--text-muted)" />
        <h3>No prediction drift data</h3>
        <p className="muted">Run the monitoring pipeline to generate prediction drift analysis.</p>
      </div>
    );
  }

  return (
    <div className="tab-panel">
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Quantile</th>
              <th className="numeric">Mean</th>
              <th className="numeric">Std Dev</th>
              <th className="numeric">KS Statistic</th>
              <th className="numeric">P-Value</th>
              <th>Drift Detected</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([quantile, info]) => (
              <tr key={quantile}>
                <td>{quantile}</td>
                <td className="numeric">{(info.mean || 0).toFixed(4)}</td>
                <td className="numeric">{(info.std || 0).toFixed(4)}</td>
                <td className="numeric">{(info.ks_statistic || 0).toFixed(4)}</td>
                <td className="numeric">{(info.p_value || 0).toFixed(4)}</td>
                <td>
                  <span className={`badge ${info.drift_detected ? 'badge-danger' : 'badge-success'}`}>
                    {info.drift_detected ? 'YES' : 'NO'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PerformanceTab({ performance }) {
  const entries = Object.entries(performance).filter(([k, v]) => v && typeof v === 'object');

  if (entries.length === 0) {
    return (
      <div className="empty-state">
        <CheckCircle size={48} color="var(--text-muted)" />
        <h3>No performance data</h3>
        <p className="muted">Run the monitoring pipeline with actuals to generate performance metrics.</p>
      </div>
    );
  }

  return (
    <div className="tab-panel">
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Quantile</th>
              <th className="numeric">RMSE</th>
              <th className="numeric">MAE</th>
              <th className="numeric">Asymmetric Cost</th>
              <th>Performance OK</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([quantile, info]) => (
              <tr key={quantile}>
                <td>{quantile}</td>
                <td className="numeric">{(info.rmse || 0).toFixed(4)}</td>
                <td className="numeric">{(info.mae || 0).toFixed(4)}</td>
                <td className="numeric">{(info.asymmetric_cost || 0).toFixed(2)}</td>
                <td>
                  <span className={`badge ${info.performance_ok ? 'badge-success' : 'badge-danger'}`}>
                    {info.performance_ok ? 'YES' : 'NO'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BacktestTab({ policies, bestPolicy }) {
  if (policies.length === 0) {
    return (
      <div className="empty-state">
        <ExternalLink size={48} color="var(--text-muted)" />
        <h3>No backtest data</h3>
        <p className="muted">Run the backtest pipeline to generate policy comparison.</p>
      </div>
    );
  }

  return (
    <div className="tab-panel">
      <div className="backtest-summary">
        <h3>Policy Comparison</h3>
        <p className="muted">Lower total cost is better. Oracle represents perfect foresight (unrealistic lower bound).</p>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Policy</th>
              <th className="numeric">Total Cost</th>
              <th className="numeric">Stockout Cost</th>
              <th className="numeric">Holding Cost</th>
              <th className="numeric">Ordering Cost</th>
              <th className="numeric">Service Level</th>
              <th className="numeric">Fill Rate</th>
              <th className="numeric">Stockout Rate</th>
              <th className="numeric">Order Rate</th>
              <th className="numeric">Avg Cost/Period</th>
              <th className="numeric">Total Orders</th>
            </tr>
          </thead>
          <tbody>
            {policies.map((policy) => (
              <tr key={policy.name} style={{ fontWeight: policy.name === bestPolicy?.name ? 700 : 400 }}>
                <td>
                  <span className={`${policy.name === bestPolicy?.name ? 'best-policy' : ''}`}>
                    {policy.name}
                    {policy.name === bestPolicy?.name && ' ⭐'}
                  </span>
                </td>
                <td className="numeric">{policy.total_cost?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                <td className="numeric">{policy.stockout_cost?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                <td className="numeric">{policy.holding_cost?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                <td className="numeric">{policy.ordering_cost?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                <td className="numeric">{(policy.service_level * 100).toFixed(1)}%</td>
                <td className="numeric">{(policy.fill_rate * 100).toFixed(1)}%</td>
                <td className="numeric">{(policy.stockout_rate * 100).toFixed(1)}%</td>
                <td className="numeric">{(policy.order_rate * 100).toFixed(1)}%</td>
                <td className="numeric">{policy.avg_cost_per_period?.toFixed(2)}</td>
                <td className="numeric">{policy.total_orders?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="backtest-chart">
        <h3>Cost Breakdown by Policy</h3>
        <CostBreakdownChart policies={policies} />
      </div>
    </div>
  );
}

function CostBreakdownChart({ policies }) {
  const operational = policies.filter(p => p.name !== 'oracle_perfect');
  const maxCost = Math.max(...operational.map(p => p.total_cost || 0), 1);
  const chartHeight = 200;

  return (
    <svg width="100%" height={chartHeight + 60} viewBox={`0 0 ${operational.length * 80 + 40} ${chartHeight + 60}`} className="bar-chart">
      {operational.map((policy, idx) => {
        const x = 30 + idx * 80;
        const stockoutH = ((policy.stockout_cost || 0) / maxCost) * chartHeight;
        const holdingH = ((policy.holding_cost || 0) / maxCost) * chartHeight;
        const orderingH = ((policy.ordering_cost || 0) / maxCost) * chartHeight;
        let y = 30 + chartHeight;

        return (
          <g key={policy.name} style={{ cursor: 'pointer' }}>
            <rect x={x + 5} y={y - stockoutH} width={30} height={stockoutH} fill="var(--danger)" opacity="0.85" rx={2} />
            <rect x={x + 5} y={y - stockoutH - holdingH} width={30} height={holdingH} fill="var(--warning)" opacity="0.85" />
            <rect x={x + 5} y={y - stockoutH - holdingH - orderingH} width={30} height={orderingH} fill="var(--accent-2)" opacity="0.85" />
            <text x={x + 20} y={30 + chartHeight + 15} textAnchor="middle" fontSize="9" fill="var(--text-muted)" transform={`rotate(-45, ${x + 20}, ${30 + chartHeight + 15})`}>
              {policy.name.slice(0, 18)}
            </text>
          </g>
        );
      })}
      <text x={10} y={20} fontSize="10" fill="var(--danger)" opacity="0.85">■ Stockout</text>
      <text x={10} y={35} fontSize="10" fill="var(--warning)" opacity="0.85">■ Holding</text>
      <text x={10} y={50} fontSize="10" fill="var(--accent-2)" opacity="0.85">■ Ordering</text>
    </svg>
  );
}

// Helper components
function KpiCard({ label, value, variant, icon: Icon }) {
  const colors = {
    success: { bg: 'var(--success-dim)', color: 'var(--success)' },
    warning: { bg: 'var(--warning-dim)', color: 'var(--warning)' },
    danger: { bg: 'var(--danger-dim)', color: 'var(--danger)' },
    info: { bg: 'var(--accent-dim)', color: 'var(--accent-2)' },
    default: { bg: 'var(--accent-dim)', color: 'var(--accent)' },
  };
  const c = colors[variant || 'default'];

  return (
    <div className="kpi-card" style={{ '--kpi-color': c.color, '--kpi-bg': c.bg }}>
      <div className="kpi-icon" style={{ background: c.bg, color: c.color }}><Icon size={20} /></div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}
