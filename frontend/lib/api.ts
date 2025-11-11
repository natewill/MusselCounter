const API_BASE = "http://127.0.0.1:8000";

export async function pingBackend() {
  const res = await fetch(`${API_BASE}/`);
  return res.json();
}

/**
 * Create a new batch
 * @param {string} [name] - Optional batch name
 * @param {string} [description] - Optional batch description
 * @returns {Promise<{batch_id: number}>} Batch ID of the created batch
 * @throws {Error} If the request fails
 */
export async function createBatch(name, description) {
  const response = await fetch(`${API_BASE}/api/batches`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: name || null,
      description: description || null,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Upload image files to a batch
 * @param {number} batchId - Batch ID to upload images to
 * @param {File[]} files - Array of image files to upload
 * @returns {Promise<{batch_id: number, image_ids: number[], count: number}>} Upload result with image IDs
 * @throws {Error} If the request fails (400: no valid files, 404: batch not found)
 */
export async function uploadImagesToBatch(batchId, files) {
  const formData = new FormData();
  
  // Append each file to FormData with key 'files'
  // FastAPI will collect them into a List[UploadFile]
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${API_BASE}/api/batches/${batchId}/upload-images`, {
    method: "POST",
    body: formData,
    // Don't set Content-Type header - browser sets it automatically with boundary for multipart/form-data
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Start an inference run on a batch
 * @param {number} batchId - Batch ID to run inference on
 * @param {number} modelId - Model ID to use for inference
 * @param {number} [threshold] - Optional threshold score for classification (defaults to 0.5)
 * @returns {Promise<{run_id?: number, batch_id: number, model_id: number, threshold: number, message?: string}>} Run information
 * @throws {Error} If the request fails (404: batch/model not found)
 */
export async function startRun(batchId, modelId, threshold) {
  const response = await fetch(`${API_BASE}/api/batches/${batchId}/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model_id: modelId,
      threshold: threshold !== undefined ? threshold : null, // Send null to use backend default
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Get all available models
 * @returns {Promise<Array<{model_id: number, name: string, type: string, weights_path: string, description?: string, created_at: string, updated_at: string}>>} Array of model objects
 * @throws {Error} If the request fails
 */
export async function getModels() {
  const response = await fetch(`${API_BASE}/api/models`, {
    method: "GET",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return await response.json();
}