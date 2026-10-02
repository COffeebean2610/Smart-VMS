import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api/cameras';

export const cameraService = {
  getAll: async () => {
    const response = await axios.get(API_URL);
    return response.data;
  },

  create: async (cameraData) => {
    const response = await axios.post(API_URL, cameraData);
    return response.data;
  },

  delete: async (id) => {
    const response = await axios.delete(`${API_URL}/${id}`);
    return response.data;
  },

  testConnection: async (streamUrl) => {
    const response = await axios.post(`${API_URL}/test`, { streamUrl });
    return response.data;
  },
  
  connect: async (id) => {
    const response = await axios.post(`${API_URL}/connect/${id}`);
    return response.data;
  },
  
  disconnect: async (id) => {
    const response = await axios.post(`${API_URL}/disconnect/${id}`);
    return response.data;
  },

  getMetrics: async (cameraId) => {
    const url = cameraId 
      ? `http://127.0.0.1:8000/api/live/metrics/${cameraId}`
      : `http://127.0.0.1:8000/api/live/metrics`;
    const response = await axios.get(url);
    return response.data;
  }
};

export const createCamera = (cameraData) => cameraService.create(cameraData);
export const testCameraConnection = (streamUrl) => cameraService.testConnection(streamUrl);


