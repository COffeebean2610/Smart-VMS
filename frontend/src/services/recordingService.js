import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api/recordings';

export const recordingService = {
  getAll: async (limit = 100) => {
    const response = await axios.get(`${API_URL}?limit=${limit}`);
    return response.data;
  },

  getById: async (id) => {
    const response = await axios.get(`${API_URL}/${id}`);
    return response.data;
  },

  getStreamUrl: (id) => {
    return `${API_URL}/${id}/stream`;
  },
  
  delete: async (id) => {
    const response = await axios.delete(`${API_URL}/${id}`);
    return response.data;
  },
  
  bulkDelete: async (filterType) => {
    const response = await axios.delete(`${API_URL}/bulk/${filterType}`);
    return response.data;
  }
};
