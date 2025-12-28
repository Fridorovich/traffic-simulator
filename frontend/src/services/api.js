import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const simulationAPI = {
  createSimulation: (config) =>
    api.post('/api/simulation/create', config),

  getSimulationState: (simId) =>
    api.get(`/api/simulation/${simId}/state`),

  stepSimulation: (simId, steps = 1) =>
    api.post(`/api/simulation/${simId}/step?steps=${steps}`),

  updateConfig: (simId, config) =>
    api.post(`/api/simulation/${simId}/config`, config),

  getMetrics: (simId) =>
    api.get(`/api/simulation/${simId}/metrics`),

  changeAlgorithm: (simId, algorithm, config = {}) =>
    api.post(`/api/simulation/${simId}/algorithm/change`, {
      algorithm,
      config
    }),

  getAlgorithms: () =>
    api.get('/api/algorithms'),
};

export default api;