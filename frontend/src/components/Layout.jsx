import { Outlet } from 'react-router-dom';
import TopBar from './TopBar';
import { SearchProvider } from '../context/SearchContext';
import './Layout.css';

export default function Layout() {
  return (
    <SearchProvider>
      <div className="layout">
        <TopBar />
        <main className="main-content" role="main">
          <div className="page-content">
            <Outlet />
          </div>
        </main>
      </div>
    </SearchProvider>
  );
}
