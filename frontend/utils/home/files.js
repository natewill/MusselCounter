/**
 * File handling utilities for home page
 */
import { uploadImagesToCollection } from '@/lib/api';
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
  activeCollectionId,
  setActiveCollectionId,
  setLoading,
  setError,
  createQuickProcessCollection,
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
    let collectionId = activeCollectionId;

    // Create collection if needed
    if (!collectionId) {
      try {
        collectionId = await createQuickProcessCollection(setActiveCollectionId);
      } catch (err) {
        console.error('Failed to create collection:', err);
        throw new Error('Failed to create collection. Is the backend running?');
      }
    }

    // Upload files
    let uploadResult;
    try {
      uploadResult = await uploadImagesToCollection(collectionId, imageFiles);
      console.log('Files uploaded successfully');
    } catch (err) {
      const errorMsg = err.message || '';
      // If collection not found (404), clear stale collection_id and create new collection
      if (errorMsg.includes('404') || errorMsg.includes('Collection not found') || errorMsg.includes('HTTP 404')) {
        console.warn('Collection not found, clearing stale collection_id and creating new collection');
        setActiveCollectionId(null);
        await safeRemoveItem('quickProcessCollectionId');
        
        // Create new collection and retry upload
        try {
          collectionId = await createQuickProcessCollection(setActiveCollectionId);
          uploadResult = await uploadImagesToCollection(collectionId, imageFiles);
          console.log('Files uploaded successfully to new collection');
        } catch (retryErr) {
          throw new Error('Failed to create new collection and upload. ' + (retryErr.message || ''));
        }
      } else {
        throw new Error('Failed to upload files. ' + errorMsg);
      }
    }

    // Store collection_id in localStorage for run page
    await safeSetItem('currentCollectionId', collectionId.toString());
    
    // Get upload counts for success message
    const addedCount = uploadResult?.added_count || 0;
    const duplicateCount = uploadResult?.duplicate_count || 0;
    const uploadedImageIds = uploadResult?.image_ids || [];
    const duplicateImageIds = uploadResult?.duplicate_image_ids || [];
    
    // Exclude duplicates from recently uploaded IDs
    const { filterNonDuplicateIds } = await import('@/utils/imageUtils');
    const nonDuplicateIds = filterNonDuplicateIds(uploadedImageIds, duplicateImageIds);
    
    // Store recently uploaded image IDs (still needed for flashing)
    await safeSetItem('recentlyUploadedImageIds', nonDuplicateIds);

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
    setError(err.message || 'Failed to process images. Make sure the backend is running.');
    setLoading(false);
    throw err;
  }
}

