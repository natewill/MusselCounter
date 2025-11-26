/**
 * Utility functions for run state management and image processing detection
 */

export interface ImageResult {
  live: number | null;
  dead: number | null;
  processed_at: string | null;
  threshold: number | null;
}

export interface Image {
  image_id: number;
  live_mussel_count: number | null;
  dead_mussel_count: number | null;
  processed_at: string | null;
  result_threshold: number | null;
  file_hash: string | null;
  processed_model_ids: number[];
}

/**
 * Build a map of current image results from collection images
 */
export function buildImageResultsMap(images: Image[]): Map<number, ImageResult> {
  const resultsMap = new Map<number, ImageResult>();
  
  images.forEach(img => {
    if (img.live_mussel_count !== null || img.dead_mussel_count !== null || img.processed_at) {
      resultsMap.set(img.image_id, {
        live: img.live_mussel_count,
        dead: img.dead_mussel_count,
        processed_at: img.processed_at,
        threshold: img.result_threshold
      });
    }
  });
  
  return resultsMap;
}

/**
 * Check if threshold changed between two values (with floating point tolerance)
 */
export function thresholdChanged(
  oldThreshold: number | null | undefined,
  newThreshold: number | null | undefined
): boolean {
  if (oldThreshold === null || oldThreshold === undefined || 
      newThreshold === null || newThreshold === undefined) {
    return false;
  }
  return Math.abs(oldThreshold - newThreshold) >= 0.001;
}

/**
 * Check if image results changed (new results, threshold change, or count change)
 */
export function resultsChanged(
  hasCurrentResults: boolean,
  hadPreviousResults: boolean,
  previousResult: ImageResult | null,
  currentImage: Image,
  latestThreshold: number | null
): boolean {
  if (!hasCurrentResults) return false;
  
  // Newly processed
  if (!hadPreviousResults) return true;
  
  if (!previousResult) return false;
  
  // Check if threshold changed from previous result
  const thresholdChangedFromPrevious = thresholdChanged(
    previousResult.threshold,
    currentImage.result_threshold
  );
  
  if (thresholdChangedFromPrevious) return true;
  
  // Check if counts changed
  const countsChanged = 
    previousResult.live !== currentImage.live_mussel_count ||
    previousResult.dead !== currentImage.dead_mussel_count;
  
  return countsChanged;
}

/**
 * Determine if an image should flash based on various conditions
 */
export function shouldFlashImage(
  image: Image,
  imageId: number,
  recentlyUploadedImageIds: Set<number>,
  isDifferentModel: boolean,
  isDifferentThreshold: boolean,
  latestModelId: number,
  latestThreshold: number | null,
  currentStatus: string | null,
  previousResult: ImageResult | null,
  duplicateImageIds: Set<number>
): boolean {
  // Skip duplicates
  if (duplicateImageIds.has(imageId)) {
    return false;
  }
  
  // Flash if recently uploaded and first time processing
  if (recentlyUploadedImageIds.has(imageId)) {
    const processedModelIds = image.processed_model_ids || [];
    if (processedModelIds.length <= 1) {
      return true;
    }
  }
  
  // Flash if processed with a different model
  if (isDifferentModel) {
    const processedModelIds = image.processed_model_ids || [];
    if (!processedModelIds.includes(latestModelId) || processedModelIds.length > 1) {
      return true;
    }
  }
  
  // Check if threshold changed
  const thresholdChangedFromCurrent = thresholdChanged(
    image.result_threshold,
    latestThreshold
  );
  const thresholdChangedFromPrevious = previousResult && 
    thresholdChanged(previousResult.threshold, image.result_threshold);
  
  // Flash if processed with a different threshold
  if (isDifferentThreshold || thresholdChangedFromCurrent || thresholdChangedFromPrevious) {
    return true;
  }
  
  // Also flash if run is active and image just got processed (for live updates)
  if (currentStatus === 'running' || currentStatus === 'pending') {
    return true;
  }
  
  return false;
}

/**
 * Find duplicate images based on file_hash
 * Returns a Set of image_ids that are duplicates (same hash appears more than once)
 * For each duplicate hash, keeps the image with the lowest image_id
 */
export function findDuplicateImageIds(images: Image[]): Set<number> {
  const hashToImages = new Map<string, Image[]>();
  
  // Group images by file_hash
  images.forEach(img => {
    if (img.file_hash) {
      if (!hashToImages.has(img.file_hash)) {
        hashToImages.set(img.file_hash, []);
      }
      hashToImages.get(img.file_hash)!.push(img);
    }
  });
  
  // Find hashes that appear more than once
  const duplicateImageIds = new Set<number>();
  hashToImages.forEach((imagesWithHash, hash) => {
    if (imagesWithHash.length > 1) {
      // Sort by image_id and keep the first one, mark others as duplicates
      const sortedImages = [...imagesWithHash].sort((a, b) => a.image_id - b.image_id);
      for (let i = 1; i < sortedImages.length; i++) {
        duplicateImageIds.add(sortedImages[i].image_id);
      }
    }
  });
  
  return duplicateImageIds;
}

/**
 * Get all processed image IDs from a collection (excluding duplicates)
 */
export function getProcessedImageIds(images: Image[]): number[] {
  const duplicateIds = findDuplicateImageIds(images);
  return images
    .filter(img => {
      const hasResults = 
        (img.live_mussel_count !== null && img.live_mussel_count !== undefined) ||
        (img.dead_mussel_count !== null && img.dead_mussel_count !== undefined) ||
        img.processed_at;
      return hasResults && !duplicateIds.has(img.image_id);
    })
    .map(img => img.image_id);
}

