import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const client = axios.create({ baseURL: API_BASE_URL, timeout: 20000 })

export const api = {
  health: () => client.get('/health').then(r => r.data),
  metadata: () => client.get('/metadata').then(r => r.data),
  stats: () => client.get('/stats').then(r => r.data),
  districts: () => client.get('/districts').then(r => r.data),
  crimeGroups: () => client.get('/crime-groups').then(r => r.data),
  crimes: (params) => client.get('/crimes', { params }).then(r => r.data),
  crimesForMap: (params) => client.get('/crimes/map', { params }).then(r => r.data),
  hotspots: (params) => client.get('/hotspots', { params }).then(r => r.data),
  riskScores: () => client.get('/risk-scores').then(r => r.data),
  modelMetrics: () => client.get('/model/metrics').then(r => r.data),
  modelFeatures: () => client.get('/model/features').then(r => r.data),
  forecast: (params) => client.get('/forecast', { params }).then(r => r.data),
  predict: (body) => client.post('/predict', body).then(r => r.data),
  explain: (body) => client.post('/explain', body).then(r => r.data),
}

export default api
