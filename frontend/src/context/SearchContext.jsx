import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Package, PackageSearch, DollarSign, TrendingUp, AlertTriangle, Tag } from 'lucide-react';

const SearchContext = createContext(null);

const MOCK_SEARCH_DATA = [
  // Products
  { id: 'p1', title: 'Trailblazer Equilibrium', subtitle: 'PROD-183453 • Scholar Footwear', category: 'Product', url: '/catalog/detail/STR-1006/PROD-183453', icon: Package },
  { id: 'p2', title: 'Flight Classic Zephyr', subtitle: 'PROD-100805 • Scholar Footwear', category: 'Product', url: '/catalog/detail/STR-1006/PROD-100805', icon: Package },
  { id: 'p3', title: 'Boot Collection Woodland', subtitle: 'PROD-140879 • Scholar Footwear', category: 'Product', url: '/catalog/detail/STR-1006/PROD-140879', icon: Package },
  { id: 'p4', title: 'Court Casual Zephyr', subtitle: 'PROD-100439 • Femme Footwear', category: 'Product', url: '/catalog/detail/STR-1198/PROD-100439', icon: Package },
  { id: 'p5', title: 'Retro Legend Summit', subtitle: 'PROD-183451 • Heritage Footwear', category: 'Product', url: '/catalog/detail/STR-1094/PROD-183451', icon: Package },
  { id: 'p6', title: 'Cozy Pullovers Varied', subtitle: 'PROD-170976 • Junior Apparel', category: 'Product', url: '/catalog/detail/STR-1157/PROD-170976', icon: Package },
  // Orders
  { id: 'o1', title: 'Order #ORD-20260115-001', subtitle: 'STR-1006 • $1,234.50 • Delivered', category: 'Order', url: '/orders/ORD-20260115-001', icon: PackageSearch },
  { id: 'o2', title: 'Order #ORD-20260114-003', subtitle: 'STR-1198 • $892.30 • Processing', category: 'Order', url: '/orders/ORD-20260114-003', icon: PackageSearch },
  { id: 'o3', title: 'Order #ORD-20260113-007', subtitle: 'STR-1094 • $2,105.75 • Shipped', category: 'Order', url: '/orders/ORD-20260113-007', icon: PackageSearch },
  // Revenue/Analytics
  { id: 'r1', title: 'January 2026 Revenue', subtitle: '$628,778 • 7,279 units sold', category: 'Analytics', url: '/analytics?period=2026-01', icon: DollarSign },
  { id: 'r2', title: 'Q4 2025 Summary', subtitle: '$1.2M revenue • 15,432 units', category: 'Analytics', url: '/analytics?period=2025-Q4', icon: DollarSign },
  { id: 'r3', title: 'Top Selling Products', subtitle: 'View leaderboard', category: 'Analytics', url: '/analytics/top-products', icon: TrendingUp },
  // Alerts/Issues
  { id: 'a1', title: 'Low Inventory Alert', subtitle: '12 products below reorder point', category: 'Alert', url: '/actions?filter=reorder', icon: AlertTriangle },
  { id: 'a2', title: 'Model Drift Detected', subtitle: '3 features exceeded PSI threshold', category: 'Alert', url: '/monitoring', icon: AlertTriangle },
  // Categories
  { id: 'c1', title: 'Scholar Footwear', subtitle: '684 products • $433K revenue', category: 'Category', url: '/catalog?division=Scholar%20Footwear', icon: Tag },
  { id: 'c2', title: 'Femme Footwear', subtitle: '523 products • $172K revenue', category: 'Category', url: '/catalog?division=Femme%20Footwear', icon: Tag },
  { id: 'c3', title: 'Junior Apparel', subtitle: '437 products • $23K revenue', category: 'Category', url: '/catalog?division=Junior%20Apparel', icon: Tag },
];

export function SearchProvider({ children }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 150);
    return () => clearTimeout(timer);
  }, [query]);

  // Filter results
  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      return;
    }
    const q = debouncedQuery.toLowerCase();
    const filtered = MOCK_SEARCH_DATA
      .filter(item =>
        item.title.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
      )
      .slice(0, 8);
    setResults(filtered);
  }, [debouncedQuery]);

  const clearResults = useCallback(() => {
    setResults([]);
    setOpen(false);
  }, []);

  return (
    <SearchContext.Provider value={{ query, setQuery, results, open, setOpen, clearResults }}>
      {children}
    </SearchContext.Provider>
  );
}

export function useSearch() {
  const context = useContext(SearchContext);
  if (!context) {
    throw new Error('useSearch must be used within SearchProvider');
  }
  return context;
}
