import { apiClient } from './client';
import { validateDetectionId, validateImageId, validateRunId } from './validators';

export async function getRunImageDetails(runId: number, runImageId: number) {
  const validatedRunId = validateRunId(runId);
  const validatedRunImageId = validateImageId(runImageId);

  const response = await apiClient.get(
    `/api/runs/${validatedRunId}/images/${validatedRunImageId}`
  );
  return response.data;
}

export async function updateRunImageDetection(
  runId: number,
  runImageId: number,
  detectionId: number,
  newClass: 'live' | 'dead'
) {
  const validatedRunId = validateRunId(runId);
  const validatedRunImageId = validateImageId(runImageId);
  const validatedDetectionId = validateDetectionId(detectionId);

  if (newClass !== 'live' && newClass !== 'dead') {
    throw new Error('Classification must be "live" or "dead"');
  }

  const response = await apiClient.patch(
    `/api/runs/${validatedRunId}/images/${validatedRunImageId}/detections/${validatedDetectionId}`,
    { new_class: newClass }
  );

  return response.data;
}

// Backward compatibility functions (old collection-based paths).
export async function getImageDetails(imageId: number, modelId: number, collectionId: number) {
  const response = await apiClient.get(`/api/images/${imageId}/results`, {
    params: {
      model_id: modelId,
      collection_id: collectionId,
    },
  });
  return response.data;
}

export async function updatePolygonClassification(
  imageId: number,
  modelId: number,
  detectionId: number,
  newClass: 'live' | 'dead',
  collectionId: number
) {
  const response = await apiClient.patch(
    `/api/images/${imageId}/results/${modelId}/detections/${detectionId}`,
    { new_class: newClass },
    {
      params: { collection_id: collectionId },
    }
  );

  return response.data;
}
