import { Outlet } from 'react-router-dom';
import { useState } from 'react';
import { Menu } from 'lucide-react';
import Sidebar from './Sidebar';
import { SearchProvider } from '../context/SearchContext';
import './Layout.css';

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <SearchProvider>
      <div className={`layout${collapsed ? ' sidebar-collapsed' : ''}`}>
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
        <main className="main-content" role="main">
          <div className="mobile-appbar"><button onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><span>STOREPULSE</span></div>
          <div className="page-content">
            <Outlet />
          </div>
        </main>
      </div>
    </SearchProvider>
  );
}
