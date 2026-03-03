export function validateCollectionId(collectionId: unknown): number {
  if (collectionId === null || collectionId === undefined) {
    throw new Error('Collection ID is required');
  }
  const id = Number(collectionId);
  if (Number.isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid collection ID');
  }
  return id;
}

export function validateModelId(modelId: unknown): number {
  if (modelId === null || modelId === undefined) {
    throw new Error('Model ID is required');
  }
  const id = Number(modelId);
  if (Number.isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid model ID');
  }
  return id;
}

export function validateThreshold(threshold: unknown): number | null {
  if (threshold === null || threshold === undefined) {
    return null;
  }
  const thresh = Number(threshold);
  if (Number.isNaN(thresh) || thresh < 0 || thresh > 1) {
    throw new Error('Threshold must be a number between 0.0 and 1.0');
  }
  return thresh;
}

export function validateRunId(runId: unknown): number {
  if (runId === null || runId === undefined) {
    throw new Error('Run ID is required');
  }
  const id = Number(runId);
  if (Number.isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid run ID');
  }
  return id;
}

export function validateImageId(imageId: unknown): number {
  if (imageId === null || imageId === undefined) {
    throw new Error('Image ID is required');
  }
  const id = Number(imageId);
  if (Number.isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid image ID');
  }
  return id;
}

export function validateDetectionId(detectionId: unknown): number {
  const id = Number(detectionId);
  if (Number.isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid detection ID');
  }
  return id;
}
