import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Package, ShoppingCart, BarChart2, TrendingUp, Settings, User, Bell, ChevronDown, Filter, X } from 'lucide-react';
import { useSearch } from '../context/SearchContext';
import './TopBar.css';

export default function TopBar() {
  const navigate = useNavigate();
  const { query, setQuery, results, open, setOpen, clearResults } = useSearch();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
      clearResults();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setOpen(false);
      clearResults();
    }
  };

  return (
    <header className="top-bar" role="banner">
      <div className="top-bar-left">
        <button className="menu-toggle" aria-label="Toggle menu">
          <Filter size={20} />
        </button>
        <div className="logo" onClick={() => navigate('/')}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          <span>StorePulse</span>
        </div>
      </div>

      <div className="top-bar-center">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-wrapper">
            <Search size={18} className="search-icon" />
            <input
              type="search"
              placeholder="Search products, orders, customers, SKUs..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setOpen(true)}
              onKeyDown={handleKeyDown}
              autoComplete="off"
              aria-label="Global search"
              aria-expanded={open && results.length > 0}
              aria-controls="search-results"
            />
            {query && (
              <button type="button" className="search-clear" onClick={() => setQuery('')} aria-label="Clear search">
                <X size={16} />
              </button>
            )}
          </div>
          {open && results.length > 0 && (
            <div id="search-results" className="search-results" role="listbox">
              {results.map((result, idx) => (
                <button
                  key={idx}
                  className="search-result-item"
                  role="option"
                  onClick={() => {
                    navigate(result.url);
                    clearResults();
                  }}
                >
                  <result.icon size={16} className="result-icon" />
                  <div className="result-content">
                    <span className="result-title">{result.title}</span>
                    <span className="result-subtitle">{result.subtitle}</span>
                  </div>
                  <span className="result-category">{result.category}</span>
                </button>
              ))}
            </div>
          )}
        </form>
      </div>

      <div className="top-bar-right">
        <div className="icon-btn-group">
          <button className="icon-btn" aria-label="Dashboard" onClick={() => navigate('/')}>
            <BarChart2 size={20} />
          </button>
          <button className="icon-btn" aria-label="Products" onClick={() => navigate('/catalog')}>
            <Package size={20} />
          </button>
          <button className="icon-btn" aria-label="Orders" onClick={() => navigate('/orders')}>
            <ShoppingCart size={20} />
          </button>
          <button className="icon-btn" aria-label="Analytics" onClick={() => navigate('/analytics')}>
            <TrendingUp size={20} />
          </button>
        </div>

        <div className="divider" />

        <div className="notifications-wrapper">
          <button className="icon-btn notification-btn" aria-label="Notifications" onClick={() => setShowNotifications(!showNotifications)}>
            <Bell size={20} />
            <span className="notification-badge">3</span>
          </button>
          {showNotifications && (
            <div className="dropdown notifications-dropdown">
              <div className="dropdown-header">
                <h3>Notifications</h3>
                <button className="mark-all-read">Mark all read</button>
              </div>
              <div className="dropdown-list">
                <div className="notification-item unread">
                  <div className="notif-icon success"><TrendingUp size={16} /></div>
                  <div className="notif-content">
                    <p className="notif-title">Sales target exceeded</p>
                    <p className="notif-time">5 min ago</p>
                  </div>
                </div>
                <div className="notification-item unread">
                  <div className="notif-icon warning"><BarChart2 size={16} /></div>
                  <div className="notif-content">
                    <p className="notif-title">Inventory low: 12 products</p>
                    <p className="notif-time">1 hour ago</p>
                  </div>
                </div>
                <div className="notification-item">
                  <div className="notif-icon info"><Package size={16} /></div>
                  <div className="notif-content">
                    <p className="notif-title">New product added: PROD-183453</p>
                    <p className="notif-time">3 hours ago</p>
                  </div>
                </div>
              </div>
              <div className="dropdown-footer">
                <button className="btn-secondary">View all</button>
              </div>
            </div>
          )}
        </div>

        <div className="divider" />

        <div className="user-menu-wrapper">
          <button className="user-btn" aria-label="User menu" onClick={() => setShowUserMenu(!showUserMenu)}>
            <div className="user-avatar">SP</div>
            <span className="user-name">StorePulse</span>
            <ChevronDown size={16} />
          </button>
          {showUserMenu && (
            <div className="dropdown user-dropdown">
              <div className="dropdown-header">
                <div className="user-info">
                  <div className="user-avatar large">SP</div>
                  <div>
                    <p className="user-name">StorePulse Admin</p>
                    <p className="user-email">admin@storepulse.com</p>
                  </div>
                </div>
              </div>
              <div className="dropdown-list">
                <button className="dropdown-item" onClick={() => navigate('/settings')}>
                  <Settings size={16} /> Settings
                </button>
                <button className="dropdown-item" onClick={() => navigate('/profile')}>
                  <User size={16} /> Profile
                </button>
                <hr className="dropdown-divider" />
                <button className="dropdown-item danger">
                  Log out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile sidebar overlay */}
      <div className="mobile-overlay" onClick={() => navigate('/')} />
    </header>
  );
}
