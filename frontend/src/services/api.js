import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health & Info
export const healthCheck = () => api.get('/health');
export const getModelInfo = () => api.get('/model/info');

// Dashboard
export const getDashboardData = () => api.get('/dashboard-data');

// Predictions
export const predict = (features) => api.post('/predict', features);
export const predictBatch = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/predict/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// Recommendations
export const getRecommendations = (features) => api.post('/recommendations', features);

// Product Alternatives
export const getProductAlternatives = (product, limit = 5) =>
  api.post('/product-alternatives', { ...product, limit });

// New endpoints we'll need (to be added to Flask)
// Product Catalog
export const getProductCatalog = (params = {}) => api.get('/catalog', { params });
export const getProductDetail = (store, productNo) => api.get(`/catalog/${store}/${productNo}`);
export const getCategoryComparison = (category, subcategory) =>
  api.get('/category-comparison', { params: { category, subcategory } });
export const getSteadyProducts = (params = {}) => api.get('/steady-products', { params });
export const getInventoryActions = (params = {}) => api.get('/inventory-actions', { params });
export const getMonitoringDetails = () => api.get('/monitoring');

// Fallback: use dashboard-data for catalog-like data
export const getCatalogFromDashboard = async () => {
  const { data } = await getDashboardData();
  // Transform dashboard data to catalog format
  return data;
};

export default api;
