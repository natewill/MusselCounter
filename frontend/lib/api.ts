import axios, { AxiosError } from 'axios';

const API_BASE = "http://127.0.0.1:8000";

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 10000, // 10 seconds default
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for uploads (longer timeout and FormData handling)
apiClient.interceptors.request.use((config) => {
  // Upload requests get longer timeout
  if (config.url?.includes('/upload-images') || config.url?.includes('/models')) {
    config.timeout = 60000; // 60 seconds for uploads
  }
  
  // Remove Content-Type header for FormData - browser will set it with boundary
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  
  return config;
});

// Response interceptor for retry logic and error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (typeof error.config & { _retryCount?: number }) | undefined;
    
    // Don't retry if request was cancelled or no config
    if (!originalRequest || error.code === 'ERR_CANCELED') {
      return Promise.reject(error);
    }
    
    // Check if error is retryable
    const status = error.response?.status;
    const isRetryable = 
      status === 429 || // Rate limited
      (status && status >= 500 && status < 600) || // Server errors
      (!error.response && error.message.includes('timeout')); // Network/timeout errors
    
    // Retry logic
    if (isRetryable && (!originalRequest._retryCount || originalRequest._retryCount < 3)) {
      originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;
      
      // Exponential backoff: 1s, 2s, 4s
      const delay = 1000 * Math.pow(2, originalRequest._retryCount - 1);
      await new Promise(resolve => setTimeout(resolve, delay));
      
      return apiClient(originalRequest);
    }
    
    // Convert to user-friendly error
    const userMessage = getUserFriendlyError(error, status);
    const userError = new Error(userMessage);
    Object.assign(userError, { originalError: error, status });
    return Promise.reject(userError);
  }
);

/**
 * Convert technical error to user-friendly message
 */
function getUserFriendlyError(error: AxiosError, status?: number): string {
  // Check if offline
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return 'You appear to be offline. Please check your internet connection and try again.';
  }
  
  // Network errors
  if (!error.response) {
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      return 'Request timed out. Please try again.';
    }
    return 'Unable to connect to the server. Please make sure the backend is running and try again.';
  }
  
  // HTTP status errors
  if (status === 404) {
    const url = error.config?.url || '';
    if (url.includes('collection') || url.includes('batch')) return 'Collection not found. It may have been deleted.';
    if (url.includes('model')) return 'Model not found. Please select a different model.';
    if (url.includes('run')) return 'Run not found.';
    return 'The requested resource was not found.';
  }
  
  if (status === 400) {
    return 'Invalid request. Please check your input and try again.';
  }
  
  if (status === 429) {
    return 'Too many requests. Please wait a moment and try again.';
  }
  
  if (status && status >= 500 && status < 600) {
    return 'Server error occurred. Please try again in a moment.';
  }
  
  // Try to get error message from response
  const errorDetail = (error.response?.data as { detail?: string })?.detail;
  if (errorDetail && typeof errorDetail === 'string' && errorDetail.length < 100) {
    return errorDetail;
  }
  
  return 'An error occurred. Please try again.';
}

/**
 * Validate batch ID
 */
function validateCollectionId(collectionId: unknown): number {
  if (collectionId === null || collectionId === undefined) {
    throw new Error('Collection ID is required');
  }
  const id = Number(collectionId);
  if (isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid collection ID');
  }
  return id;
}

/**
 * Validate model ID
 */
function validateModelId(modelId: unknown): number {
  if (modelId === null || modelId === undefined) {
    throw new Error('Model ID is required');
  }
  const id = Number(modelId);
  if (isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid model ID');
  }
  return id;
}

/**
 * Validate threshold
 */
function validateThreshold(threshold: unknown): number | null {
  if (threshold === null || threshold === undefined) {
    return null; // Allow null to use backend default
  }
  const thresh = Number(threshold);
  if (isNaN(thresh) || thresh < 0 || thresh > 1) {
    throw new Error('Threshold must be a number between 0.0 and 1.0');
  }
  return thresh;
}

export async function pingBackend() {
  const response = await apiClient.get('/');
  return response.data;
}

/**
 * Create a new collection
 */
export async function createCollection(name?: string, description?: string) {
  const response = await apiClient.post('/api/collections', {
      name: name || null,
      description: description || null,
  });
  return response.data;
}

/**
 * Upload image files to a collection
 */
export async function uploadImagesToCollection(collectionId: number, files: File[]) {
  const validatedCollectionId = validateCollectionId(collectionId);
  
  if (!files || !Array.isArray(files) || files.length === 0) {
    throw new Error('No files provided');
  }
  
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
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

/**
 * Start an inference run on a collection
 */
export async function startRun(collectionId: number, modelId: number, threshold?: number) {
  const validatedCollectionId = validateCollectionId(collectionId);
  const validatedModelId = validateModelId(modelId);
  const validatedThreshold = validateThreshold(threshold);
  
  const response = await apiClient.post(
    `/api/collections/${validatedCollectionId}/run`,
    {
      model_id: validatedModelId,
      threshold: validatedThreshold,
    }
  );
  
  return response.data;
}

/**
 * Get all available models
 */
export async function getModels() {
  const response = await apiClient.get('/api/models');
  return response.data;
}

/**
 * Upload a new model file
 */
export async function uploadModel(
  file: File,
  name?: string,
  modelType?: string,
  description?: string
) {
  const formData = new FormData();
  formData.append('file', file);
  if (name) formData.append('name', name);
  if (modelType) formData.append('model_type', modelType);
  if (description) formData.append('description', description);
  
  try {
    // Don't set Content-Type header - axios will set it automatically with boundary
    const response = await apiClient.post('/api/models', formData);
    return response.data;
  } catch (error) {
    console.error('[uploadModel] Request failed:', {
      error,
      response: error.response,
      status: error.response?.status,
      data: error.response?.data,
      headers: error.response?.headers
    });
    throw error;
  }
}

/**
 * Get collection details including images and latest run
 */
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

/**
 * Get database version to detect resets
 */
export async function getDbVersion() {
  const response = await apiClient.get('/api/db-version');
  return response.data;
}

/**
 * Get run information
 */
export async function getRun(runId: number) {
  if (runId === null || runId === undefined) {
    throw new Error('Run ID is required');
  }
  const id = Number(runId);
  if (isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid run ID');
  }
  
  const response = await apiClient.get(`/api/runs/${id}`);
  return response.data;
}

/**
 * Stop/cancel a running inference run
 */
export async function stopRun(runId: number) {
  if (runId === null || runId === undefined) {
    throw new Error('Run ID is required');
  }
  const id = Number(runId);
  if (isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid run ID');
  }
  
  const response = await apiClient.post(`/api/runs/${id}/stop`, {});
  return response.data;
}

/**
 * Remove an image from a collection
 */
export async function deleteImageFromCollection(collectionId: number, imageId: number) {
  const validatedCollectionId = validateCollectionId(collectionId);
  
  if (imageId === null || imageId === undefined) {
    throw new Error('Image ID is required');
  }
  const id = Number(imageId);
  if (isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid image ID');
  }
  
  const response = await apiClient.delete(
    `/api/collections/${validatedCollectionId}/images/${id}`
  );
  
  return response.data;
}

/**
 * Validate image ID
 */
function validateImageId(imageId: unknown): number {
  if (imageId === null || imageId === undefined) {
    throw new Error('Image ID is required');
  }
  const id = Number(imageId);
  if (isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid image ID');
  }

  return id
}

/**
 * Validate run ID
 */
function validateRunId(runId: unknown): number {
  if (runId === null || runId === undefined) {
    throw new Error('Run ID is required');
  }
  const rid = Number(runId);
  if (isNaN(rid) || rid <= 0 || !Number.isInteger(rid)) {
    throw new Error('Invalid run ID');
  }
  return rid
}

/**
 * gets image details from a specific run
 */
export async function getImageDetails(imageId: number, runId: number) {
  const validatedImageId = validateImageId(imageId);
  const validatedRunId = validateRunId(runId);
  
  const response = await apiClient.get(`/api/images/${validatedImageId}/results/${validatedRunId}`);
  return response.data;
}

/**
 * change the label of a polygon/mussel
 */
export async function updatePolygonClassification(
  imageId: number,
  runId: number,
  polygonIndex: number,
  newClass: 'live' | 'dead'
) {
  const validatedImageId = validateImageId(imageId);
  const validatedRunId = validateRunId(runId);

  if (newClass !== 'live' && newClass !== 'dead') {
    throw new Error('Classification must be "live" or "dead"');
  }

  const response = await apiClient.patch(
    `/api/images/${validatedImageId}/results/${validatedRunId}/polygons/${polygonIndex}`,
    { new_class: newClass }
  );

  return response.data;
}

/**
 * Recalculate mussel counts for a collection with a new threshold
 * without re-running the model. Uses stored detection data.
 */
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
        model_id: validatedModelId
      }
    }
  );

  return response.data;
}
