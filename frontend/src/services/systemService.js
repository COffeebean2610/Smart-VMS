import api from './api';

export const getDbStatus = async () => {
  const response = await api.get('/system/db-status');
  return response.data;
};

export const getDbConfig = async () => {
  const response = await api.get('/system/db-config');
  return response.data;
};

export const saveDbConfig = async (mongoUri) => {
  const response = await api.post('/system/db-config', { mongoUri });
  return response.data;
};

export const getFirstRunStatus = async () => {
  const response = await api.get('/system/first-run');
  return response.data;
};

export const completeFirstRun = async () => {
  const response = await api.post('/system/first-run/complete');
  return response.data;
};

