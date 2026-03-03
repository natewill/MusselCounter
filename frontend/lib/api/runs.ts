import { apiClient } from './client';
import { validateModelId, validateRunId, validateThreshold } from './validators';

export async function createRun(modelId: number, threshold: number, files: File[]) {
  const validatedModelId = validateModelId(modelId);
  const validatedThreshold = validateThreshold(threshold);

  if (!files || files.length === 0) {
    throw new Error('At least one image is required');
  }

  const formData = new FormData();
  formData.append('model_id', String(validatedModelId));
  formData.append('threshold', String(validatedThreshold ?? threshold));
  for (const file of files) {
    formData.append('files', file);
  }

  const response = await apiClient.post('/api/runs', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

export async function listRuns() {
  const response = await apiClient.get('/api/runs');
  return response.data;
}

export async function getRunDetail(runId: number) {
  const id = validateRunId(runId);
  const response = await apiClient.get(`/api/runs/${id}`);
  return response.data;
}

export async function deleteRunById(runId: number) {
  const id = validateRunId(runId);
  const response = await apiClient.delete(`/api/runs/${id}`);
  return response.data;
}

export async function recalculateRunThreshold(runId: number, threshold: number) {
  const id = validateRunId(runId);
  const validatedThreshold = validateThreshold(threshold);
  const response = await apiClient.get(`/api/runs/${id}/recalculate`, {
    params: {
      threshold: validatedThreshold ?? threshold,
    },
  });
  return response.data;
}

// Backward compatibility exports for old code paths.
export async function startRun(_collectionId: number, _modelId: number, _threshold?: number) {
  throw new Error('startRun is no longer supported. Use createRun(modelId, threshold, files).');
}

export async function getRun(runId: number) {
  return getRunDetail(runId);
}

export async function stopRun(_runId: number) {
  throw new Error('stopRun is no longer supported in run-first flow.');
}
