import { apiClient } from './client';
import { validateCollectionId, validateModelId } from './validators';

export async function createCollection(name?: string) {
  const response = await apiClient.post('/api/collections', {
    name: name || null,
  });
  return response.data;
}

export async function getCollections() {
  const response = await apiClient.get('/api/collections');
  return response.data;
}

export async function updateCollection(
  collectionId: number,
  updates: { name?: string }
) {
  const validatedCollectionId = validateCollectionId(collectionId);
  const response = await apiClient.patch(
    `/api/collections/${validatedCollectionId}`,
    updates
  );
  return response.data;
}

export async function deleteCollection(collectionId: number) {
  const validatedCollectionId = validateCollectionId(collectionId);
  const response = await apiClient.delete(`/api/collections/${validatedCollectionId}`);
  return response.data;
}

export async function uploadImagesToCollection(collectionId: number, files: File[]) {
  const validatedCollectionId = validateCollectionId(collectionId);

  if (!files || !Array.isArray(files) || files.length === 0) {
    throw new Error('No files provided');
  }

  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const response = await apiClient.post(
    `/api/collections/${validatedCollectionId}/upload-images`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
}

export async function getCollection(collectionId: number, modelId?: number | null) {
  const validatedCollectionId = validateCollectionId(collectionId);
  const params = new URLSearchParams();
  if (modelId !== null && modelId !== undefined) {
    params.set('model_id', modelId.toString());
  }
  const queryString = params.toString();
  const url = `/api/collections/${validatedCollectionId}${queryString ? `?${queryString}` : ''}`;
  const response = await apiClient.get(url);
  return response.data;
}

export async function recalculateThreshold(
  collectionId: number,
  threshold: number,
  modelId: number
) {
  const validatedCollectionId = validateCollectionId(collectionId);
  const validatedModelId = validateModelId(modelId);

  if (threshold < 0 || threshold > 1) {
    throw new Error('Threshold must be between 0 and 1');
  }

  const response = await apiClient.get(
    `/api/collections/${validatedCollectionId}/recalculate`,
    {
      params: {
        threshold,
        model_id: validatedModelId,
      },
    }
  );

  return response.data;
}

export async function deleteImageFromCollection(collectionId: number, imageId: number) {
  const validatedCollectionId = validateCollectionId(collectionId);

  if (imageId === null || imageId === undefined) {
    throw new Error('Image ID is required');
  }
  const id = Number(imageId);
  if (Number.isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid image ID');
  }

  const response = await apiClient.delete(
    `/api/collections/${validatedCollectionId}/images/${id}`
  );

  return response.data;
}
