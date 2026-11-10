const $ = (id) => document.getElementById(id);
const number = (value) => new Intl.NumberFormat().format(value || 0);

function renderDashboard(data) {
  $('store-products').textContent = number(data.dataset.store_products);
  $('feature-rows').textContent = number(data.dataset.rows);
  $('drift-count').textContent = number(data.monitoring.drift_count);
  $('best-cost').textContent = data.backtest.best_policy ? Number(data.backtest.best_policy.total_cost).toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—';
  $('best-policy').textContent = data.backtest.best_policy ? data.backtest.best_policy.name : 'no backtest artifact';
  $('model-name').textContent = data.model.name + (data.model.loaded ? ' · loaded' : ' · API starts on demand');
  $('date-range').textContent = data.dataset.date_range.length ? `${data.dataset.date_range[0].slice(0, 10)} → ${data.dataset.date_range[1].slice(0, 10)}` : '—';
  $('monitor-time').textContent = data.monitoring.timestamp ? new Date(data.monitoring.timestamp).toLocaleString() : '—';
  $('web-status').textContent = data.web_search.configured ? `${data.web_search.provider} ready` : 'API key required';
  $('web-status').classList.toggle('green', data.web_search.configured);
  $('status-text').textContent = 'Dashboard connected';
  $('drift-list').innerHTML = data.monitoring.drifted_features.length ? data.monitoring.drifted_features.map((name) => `<span class="chip">${name}</span>`).join('') : '<span class="muted">No drift alerts</span>';
  $('policy-list').innerHTML = data.backtest.policies.length ? data.backtest.policies.map((policy) => `<div class="policy"><span>${policy.name}</span><strong>${Number(policy.total_cost).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></div>`).join('') : '<span class="muted">No backtest artifact</span>';
}

async function loadDashboard() {
  try {
    const response = await fetch('/dashboard-data');
    if (!response.ok) throw new Error('Dashboard data unavailable');
    renderDashboard(await response.json());
  } catch (error) {
    $('status-text').textContent = error.message;
    $('status-dot').style.background = 'var(--danger)';
  }
}

function renderAlternatives(payload) {
  const results = payload.alternatives || [];
  $('alternative-results').innerHTML = results.length ? results.map((item) => `<div class="result"><a href="${item.url}" target="_blank" rel="noreferrer">${item.title}</a><div class="result-meta">${Math.round(item.value_quality_score * 100)}% value/quality · ${item.rating ? `${item.rating}/5 · ` : ''}${item.price ? item.price.toFixed(2) : 'price unavailable'} · ${item.source}</div><p>${item.snippet || 'No summary available.'}</p></div>`).join('') : '<p class="muted">No alternatives found.</p>';
}

$('alternative-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button');
  button.disabled = true;
  $('alternative-results').innerHTML = '<p class="muted">Searching the public web…</p>';
  const payload = Object.fromEntries(new FormData(form));
  if (payload.unit_price) payload.unit_price = Number(payload.unit_price);
  try {
    const response = await fetch('/product-alternatives', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Search failed');
    renderAlternatives(data);
  } catch (error) {
    $('alternative-results').innerHTML = `<p class="muted">${error.message}</p>`;
  } finally { button.disabled = false; }
});

loadDashboard();
