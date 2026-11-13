import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Activity, BarChart3, Boxes, ChevronLeft, CircleHelp, ClipboardCheck, LayoutDashboard, PackageSearch, Search, Settings, Sparkles, X } from 'lucide-react';
import { useSearch } from '../context/SearchContext';
import './Sidebar.css';

const navigation = [
  { label: 'Overview', to: '/', icon: LayoutDashboard, end: true },
  { label: 'Product catalog', to: '/catalog', icon: Boxes },
  { label: 'Inventory actions', to: '/actions', icon: ClipboardCheck },
  { label: 'Category analysis', to: '/comparison', icon: BarChart3 },
  { label: 'Slow movers', to: '/steady', icon: PackageSearch },
  { label: 'Model health', to: '/monitoring', icon: Activity },
];

export default function Sidebar({ collapsed, onToggle, mobileOpen, onClose }) {
  const navigate = useNavigate();
  const { query, setQuery, clearResults } = useSearch();
  const [searchFocused, setSearchFocused] = useState(false);

  const submitSearch = (event) => {
    event.preventDefault();
    const term = query.trim();
    if (!term) return;
    navigate(`/catalog?search=${encodeURIComponent(term)}`);
    clearResults();
    onClose();
  };

  return (
    <>
      {mobileOpen && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={onClose} />}
      <aside className={`app-sidebar${collapsed ? ' is-collapsed' : ''}${mobileOpen ? ' is-mobile-open' : ''}`} aria-label="Main navigation">
        <div className="sidebar-brand-row">
          <button className="brand-lockup" onClick={() => { navigate('/'); onClose(); }} aria-label="StorePulse home">
            <span className="brand-mark"><i /><i /><i /><i /></span>
            {!collapsed && <span className="brand-name">STOREPULSE</span>}
          </button>
          <button className="sidebar-collapse" onClick={onToggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {mobileOpen ? <X size={16} /> : <ChevronLeft className={collapsed ? 'flip' : ''} size={16} />}
          </button>
        </div>

        {!collapsed && <form className={`sidebar-search${searchFocused ? ' focused' : ''}`} onSubmit={submitSearch}>
          <Search size={15} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} onFocus={() => setSearchFocused(true)} onBlur={() => setSearchFocused(false)} placeholder="Search" aria-label="Search products" />
          {query && <button type="button" onClick={() => setQuery('')} aria-label="Clear search"><X size={13} /></button>}
        </form>}

        <nav className="sidebar-nav">
          <span className="sidebar-label">WORKSPACE</span>
          {navigation.map(({ label, to, icon: Icon, end }) => <NavLink key={to} to={to} end={end} title={collapsed ? label : undefined} onClick={onClose} className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <Icon size={17} strokeWidth={1.8} /><span>{label}</span>
          </NavLink>)}
        </nav>

        <div className="sidebar-bottom">
          {!collapsed && <div className="sidebar-tip"><span><Sparkles size={14} /></span><strong>Decisions, made clearer</strong><p>Recommendations are built for review and action.</p></div>}
          <button className="sidebar-help" onClick={() => navigate('/monitoring')} title={collapsed ? 'Help & support' : undefined}><CircleHelp size={17} /><span>Help &amp; support</span></button>
          <div className="sidebar-profile">
            <span className="profile-avatar">SP</span>
            {!collapsed && <span className="profile-copy"><strong>StorePulse Admin</strong><small>Retail workspace</small></span>}
            {!collapsed && <Settings size={16} className="profile-settings" />}
          </div>
        </div>
      </aside>
    </>
  );
}
