import { apiClient } from './client';

export async function pingBackend() {
  const response = await apiClient.get('/');
  return response.data;
}

export async function getDbVersion() {
  const response = await apiClient.get('/api/db-version');
  return response.data;
}
