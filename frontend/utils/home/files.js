/**
 * File handling utilities for home page
 */
import { createCollection, uploadImagesToCollection } from '@/lib/api';
import { validateImageFiles } from '@/utils/validation';

/**
 * Recursively traverse a directory entry and collect all files
 */
async function traverseDirectory(entry) {
  const files = [];
  
  if (entry.isFile) {
    const file = await new Promise((resolve, reject) => {
      entry.file(resolve, reject);
    });
    files.push(file);
  } else if (entry.isDirectory) {
    const reader = entry.createReader();
    const entries = await new Promise((resolve, reject) => {
      reader.readEntries(resolve, reject);
    });
    
    for (const childEntry of entries) {
      const childFiles = await traverseDirectory(childEntry);
      files.push(...childFiles);
    }
  }
  
  return files;
}

/**
 * Handle dropped items (supports both files and folders)
 */
export async function handleDroppedItems(dataTransferItems) {
  const allFiles = [];
  
  for (const item of dataTransferItems) {
    if (item.kind === 'file') {
      const entry = item.webkitGetAsEntry();
      if (entry) {
        const files = await traverseDirectory(entry);
        allFiles.push(...files);
      }
    }
  }
  
  return allFiles;
}

export async function handleFileSelect(
  files,
  setLoading,
  setError,
  router
) {
  const { validFiles: imageFiles, errors: validationErrors } = validateImageFiles(files);

  if (imageFiles.length === 0) {
    setError(validationErrors.join(' ') || 'Please select valid image files');
    return;
  }
  
  // Show warnings for invalid files but continue with valid ones
  if (validationErrors.length > 0) {
    console.warn('Some files were skipped:', validationErrors);
  }

  setLoading(true);
  setError(null);

  try {
    const name = `Quick Process - ${new Date().toLocaleString()}`;
    const { collection_id: collectionId } = await createCollection(name);
    const uploadResult = await uploadImagesToCollection(collectionId, imageFiles);

    // Get upload counts for success message
    const addedCount = uploadResult?.added_count || 0;
    const duplicateCount = uploadResult?.duplicate_count || 0;
    
    // Navigate to collection page with upload counts in URL query params
    // The collection page will show "X images added!" and a button to start the run
    const params = new URLSearchParams();
    if (addedCount > 0) {
      params.set('added', addedCount.toString());
    }
    if (duplicateCount > 0) {
      params.set('duplicates', duplicateCount.toString());
    }
    const queryString = params.toString();
    router.push(`/collection/${collectionId}${queryString ? `?${queryString}` : ''}`);
    
    // Don't set loading to false - let the run page handle its own loading state
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to process images. Make sure the backend is running.';
    setError(message);
    setLoading(false);
    throw err;
  }
}
