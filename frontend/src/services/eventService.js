import api from './api';

export const eventService = {
  getAll: async (limit = 50) => {
    const response = await api.get(`/events/?limit=${limit}`);
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`/events/${id}`);
    return response.data;
  },
  create: async (data) => {
    const response = await api.post('/events/', data);
    return response.data;
  },
  delete: async (id) => {
    const response = await api.delete(`/events/${id}`);
    return response.data;
  },
  bulkDelete: async (filterType) => {
    const response = await api.delete(`/events/bulk/${filterType}`);
    return response.data;
  }
};
