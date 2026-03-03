import axios, { AxiosError } from 'axios';
import { getApiBase } from './base';

export const apiClient = axios.create({
  baseURL: getApiBase(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  if (config.url?.includes('/upload-images') || config.url?.includes('/models')) {
    config.timeout = 60000;
  }

  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (typeof error.config & { _retryCount?: number }) | undefined;

    if (!originalRequest || error.code === 'ERR_CANCELED') {
      return Promise.reject(error);
    }

    const status = error.response?.status;
    const isRetryable =
      status === 429 ||
      (status && status >= 500 && status < 600) ||
      (!error.response && error.message.includes('timeout'));

    if (isRetryable && (!originalRequest._retryCount || originalRequest._retryCount < 3)) {
      originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;

      const delay = 1000 * Math.pow(2, originalRequest._retryCount - 1);
      await new Promise((resolve) => setTimeout(resolve, delay));

      return apiClient(originalRequest);
    }

    const userMessage = getUserFriendlyError(error, status);
    const userError = new Error(userMessage);
    Object.assign(userError, { originalError: error, status });
    return Promise.reject(userError);
  }
);

function getUserFriendlyError(error: AxiosError, status?: number): string {
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return 'You appear to be offline. Please check your internet connection and try again.';
  }

  if (!error.response) {
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      return 'Request timed out. Please try again.';
    }
    return 'Unable to connect to the server. Please make sure the backend is running and try again.';
  }

  if (status === 404) {
    const url = error.config?.url || '';
    if (url.includes('collection') || url.includes('batch')) return 'Collection not found. It may have been deleted.';
    if (url.includes('model')) return 'Model not found. Please select a different model.';
    if (url.includes('run')) return 'Run not found.';
    return 'The requested resource was not found.';
  }

  if (status === 400) {
    const errorDetail = (error.response?.data as { detail?: string })?.detail;
    if (errorDetail && typeof errorDetail === 'string' && errorDetail.length < 200) {
      return errorDetail;
    }
    return 'Invalid request. Please check your input and try again.';
  }

  if (status === 429) {
    return 'Too many requests. Please wait a moment and try again.';
  }

  if (status && status >= 500 && status < 600) {
    return 'Server error occurred. Please try again in a moment.';
  }

  const errorDetail = (error.response?.data as { detail?: string })?.detail;
  if (errorDetail && typeof errorDetail === 'string' && errorDetail.length < 100) {
    return errorDetail;
  }

  return 'An error occurred. Please try again.';
}
