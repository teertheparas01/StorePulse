import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ProductCatalog from './pages/ProductCatalog';
import ProductDetail from './pages/ProductDetail';
import InventoryActions from './pages/InventoryActions';
import CategoryComparison from './pages/CategoryComparison';
import SteadyLowVolume from './pages/SteadyLowVolume';
import ModelMonitoring from './pages/ModelMonitoring';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/catalog" element={<ProductCatalog />} />
          <Route path="/catalog/detail/:store/:productNo" element={<ProductDetail />} />
          <Route path="/actions" element={<InventoryActions />} />
          <Route path="/comparison" element={<CategoryComparison />} />
          <Route path="/steady" element={<SteadyLowVolume />} />
          <Route path="/monitoring" element={<ModelMonitoring />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
