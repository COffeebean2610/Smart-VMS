import api from './api';

export const roiService = {
  getAll: async () => {
    const response = await api.get('/roi');
    return response.data;
  },
  create: async (data) => {
    const response = await api.post('/roi', data);
    return response.data;
  },
  update: async (id, data) => {
    const response = await api.put(`/roi/${id}`, data);
    return response.data;
  },
  delete: async (id) => {
    const response = await api.delete(`/roi/${id}`);
    return response.data;
  }
};
