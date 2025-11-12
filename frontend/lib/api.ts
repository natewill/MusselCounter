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

// Request interceptor for uploads (longer timeout)
apiClient.interceptors.request.use((config) => {
  // Upload requests get longer timeout
  if (config.url?.includes('/upload-images')) {
    config.timeout = 60000; // 60 seconds for uploads
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
    if (url.includes('batch')) return 'Batch not found. It may have been deleted.';
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
function validateBatchId(batchId: unknown): number {
  if (batchId === null || batchId === undefined) {
    throw new Error('Batch ID is required');
  }
  const id = Number(batchId);
  if (isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid batch ID');
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
 * Create a new batch
 */
export async function createBatch(name?: string, description?: string) {
  const response = await apiClient.post('/api/batches', {
      name: name || null,
      description: description || null,
  });
  return response.data;
}

/**
 * Upload image files to a batch
 */
export async function uploadImagesToBatch(batchId: number, files: File[]) {
  const validatedBatchId = validateBatchId(batchId);
  
  if (!files || !Array.isArray(files) || files.length === 0) {
    throw new Error('No files provided');
  }
  
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  
  const response = await apiClient.post(
    `/api/batches/${validatedBatchId}/upload-images`,
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
 * Start an inference run on a batch
 */
export async function startRun(batchId: number, modelId: number, threshold?: number) {
  const validatedBatchId = validateBatchId(batchId);
  const validatedModelId = validateModelId(modelId);
  const validatedThreshold = validateThreshold(threshold);
  
  const response = await apiClient.post(
    `/api/batches/${validatedBatchId}/run`,
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
 * Get batch details including images and latest run
 */
export async function getBatch(batchId: number) {
  const validatedBatchId = validateBatchId(batchId);
  const response = await apiClient.get(`/api/batches/${validatedBatchId}`);
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
 * Remove an image from a batch
 */
export async function deleteImageFromBatch(batchId: number, imageId: number) {
  const validatedBatchId = validateBatchId(batchId);
  
  if (imageId === null || imageId === undefined) {
    throw new Error('Image ID is required');
  }
  const id = Number(imageId);
  if (isNaN(id) || id <= 0 || !Number.isInteger(id)) {
    throw new Error('Invalid image ID');
  }
  
  const response = await apiClient.delete(
    `/api/batches/${validatedBatchId}/images/${id}`
  );
  
  return response.data;
}
