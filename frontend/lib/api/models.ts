import { apiClient } from './client';

export async function getModels() {
  const response = await apiClient.get('/api/models');
  return response.data;
}

export async function uploadModel(
  file: File,
  modelType: 'YOLO' | 'FASTRCNN',
  name?: string
) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('model_type', modelType);
  if (name) formData.append('name', name);

  try {
    const response = await apiClient.post('/api/models', formData);
    return response.data;
  } catch (error) {
    console.error('[uploadModel] Request failed');
    throw error;
  }
}
