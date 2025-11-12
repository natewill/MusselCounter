/**
 * File handling utilities for home page
 */
import { uploadImagesToBatch } from '@/lib/api';
import { safeSetItem, safeRemoveItem } from '@/utils/storage';
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
  activeBatchId,
  setActiveBatchId,
  selectedModelId,
  setLoading,
  setError,
  createQuickProcessBatch,
  router
) {
  const { validFiles: imageFiles, errors: validationErrors } = validateImageFiles(files);

  if (imageFiles.length === 0) {
    if (validationErrors.length > 0) {
      setError(validationErrors.join(' '));
    } else {
      setError('Please select valid image files');
    }
    return;
  }
  
  // Show warnings for invalid files but continue with valid ones
  if (validationErrors.length > 0) {
    console.warn('Some files were skipped:', validationErrors);
  }

  setLoading(true);
  setError(null);

  try {
    let batchId = activeBatchId;

    // Create batch if needed
    if (!batchId) {
      try {
        batchId = await createQuickProcessBatch(setActiveBatchId);
      } catch (err) {
        console.error('Failed to create batch:', err);
        throw new Error('Failed to create batch. Is the backend running?');
      }
    }

    // Upload files
    let uploadResult;
    try {
      uploadResult = await uploadImagesToBatch(batchId, imageFiles);
      console.log('Files uploaded successfully');
    } catch (err) {
      const errorMsg = err.message || '';
      // If batch not found (404), clear stale batch_id and create new batch
      if (errorMsg.includes('404') || errorMsg.includes('Batch not found') || errorMsg.includes('HTTP 404')) {
        console.warn('Batch not found, clearing stale batch_id and creating new batch');
        setActiveBatchId(null);
        await safeRemoveItem('quickProcessBatchId');
        
        // Create new batch and retry upload
        try {
          batchId = await createQuickProcessBatch(setActiveBatchId);
          uploadResult = await uploadImagesToBatch(batchId, imageFiles);
          console.log('Files uploaded successfully to new batch');
        } catch (retryErr) {
          throw new Error('Failed to create new batch and upload. ' + (retryErr.message || ''));
        }
      } else {
        throw new Error('Failed to upload files. ' + errorMsg);
      }
    }

    // Store batch_id in localStorage for run page
    await safeSetItem('currentBatchId', batchId.toString());
    
    // Store upload counts in localStorage to show success message
    const addedCount = uploadResult?.added_count || 0;
    const duplicateCount = uploadResult?.duplicate_count || 0;
    const uploadedImageIds = uploadResult?.image_ids || [];
    const duplicateImageIds = uploadResult?.duplicate_image_ids || [];
    
    // Exclude duplicates from recently uploaded IDs
    const { filterNonDuplicateIds } = await import('@/utils/imageUtils');
    const nonDuplicateIds = filterNonDuplicateIds(uploadedImageIds, duplicateImageIds);
    
    await safeSetItem('uploadedImageCount', addedCount.toString());
    await safeSetItem('duplicateImageCount', duplicateCount.toString());
    await safeSetItem('recentlyUploadedImageIds', nonDuplicateIds);
    
    // Navigate to run page with batch_id (don't start run yet)
    // The run page will show "X images added!" and a button to start the run
    router.push(`/run/${batchId}`);
    
    // Don't set loading to false - let the run page handle its own loading state
  } catch (err) {
    setError(err.message || 'Failed to process images. Make sure the backend is running.');
    setLoading(false);
    throw err;
  }
}

