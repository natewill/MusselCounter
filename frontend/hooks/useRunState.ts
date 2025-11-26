import { useState, useEffect, useRef, startTransition } from 'react';
import {
  buildImageResultsMap,
  resultsChanged,
  shouldFlashImage,
  getProcessedImageIds,
  findDuplicateImageIds,
  type ImageResult
} from '@/utils/run/runUtils';

interface Image {
  image_id: number;
  live_mussel_count: number | null;
  dead_mussel_count: number | null;
  processed_at: string | null;
  result_threshold: number | null;
  file_hash: string | null;
  processed_model_ids: number[];
}

interface LatestRun {
  status: string;
  run_id: number;
  model_id: number;
  threshold: number;
}

interface BatchData {
  images: Image[];
  latest_run: LatestRun | null;
}

export function useRunState(
  batchData: BatchData | undefined,
  recentlyUploadedImageIds: Set<number>,
  setRecentlyUploadedImageIds: (ids: Set<number> | ((prev: Set<number>) => Set<number>)) => void
) {
  const [flashingImageIds, setFlashingImageIds] = useState<Set<number>>(new Set());
  const [greenHueImageIds, setGreenHueImageIds] = useState<Set<number>>(new Set());
  const [previousRunStatus, setPreviousRunStatus] = useState<string | null>(null);
  const [previousRunModelId, setPreviousRunModelId] = useState<number | null>(null);
  const [previousRunThreshold, setPreviousRunThreshold] = useState<number | null>(null);
  const [flashedImageIds, setFlashedImageIds] = useState<Set<number>>(new Set());
  const previousImageResultsRef = useRef<Map<number, ImageResult>>(new Map());

  // Detect when new images are processed and trigger green flash
  useEffect(() => {
    const currentStatus = batchData?.latest_run?.status;
    const latestRunId = batchData?.latest_run?.run_id;
    const latestModelId = batchData?.latest_run?.model_id;
    const latestThreshold = batchData?.latest_run?.threshold;
    
    if (!batchData?.images || !latestRunId || !latestModelId) {
      return;
    }
    
    // Reset flashed images and green hue when a new run starts
    if (currentStatus === 'pending' || (currentStatus === 'running' && previousRunStatus !== 'running' && previousRunStatus !== 'pending')) {
      startTransition(() => {
        setFlashedImageIds(new Set());
        setGreenHueImageIds(new Set());
        setFlashingImageIds(new Set());
      });
      previousImageResultsRef.current = new Map();
    }
    
    // Determine if this is a different model or threshold than the previous run
    const isDifferentModel = previousRunModelId !== null && previousRunModelId !== latestModelId;
    const isDifferentThreshold = previousRunThreshold !== null && previousRunThreshold !== latestThreshold;
    
    // Build a map of current image results
    const currentImageResults = buildImageResultsMap(batchData.images);
    
    // Find duplicate images based on file_hash
    const duplicateImageIds = findDuplicateImageIds(batchData.images);
    
    // Find images that just got results (newly processed or reprocessed with new threshold)
    const newlyProcessedIds: number[] = [];
    
    for (const img of batchData.images) {
      const imageId = img.image_id;
      
      // Skip if already flashed in this run
      if (flashedImageIds.has(imageId)) {
        continue;
      }
      
      // Skip duplicates
      if (duplicateImageIds.has(imageId)) {
        continue;
      }
      
      // Check if this image has current results
      const hasCurrentResults = currentImageResults.has(imageId);
      const hadPreviousResults = previousImageResultsRef.current.has(imageId);
      const previousResult = hadPreviousResults ? previousImageResultsRef.current.get(imageId) : null;
      
      // Check if results changed (new results or reprocessed with new threshold)
      const imageResultsChanged = resultsChanged(
        hasCurrentResults,
        hadPreviousResults,
        previousResult,
        img,
        latestThreshold
      );
      
      if (imageResultsChanged) {
        // Image just got results or was reprocessed - check if it should flash
        const shouldFlash = shouldFlashImage(
          img,
          imageId,
          recentlyUploadedImageIds,
          isDifferentModel,
          isDifferentThreshold,
          latestModelId,
          latestThreshold,
          currentStatus,
          previousResult,
          duplicateImageIds
        );
        
        if (shouldFlash) {
          newlyProcessedIds.push(imageId);
        }
      }
    }
    
    // Add newly processed images to green hue set (persistent during run)
    if (newlyProcessedIds.length > 0) {
      startTransition(() => {
        // Add to green hue set (persistent until run completes)
        setGreenHueImageIds(prev => {
          const newSet = new Set(prev);
          newlyProcessedIds.forEach(id => newSet.add(id));
          return newSet;
        });
        
        // Mark as flashed
        setFlashedImageIds(prev => {
          const newSet = new Set(prev);
          newlyProcessedIds.forEach(id => newSet.add(id));
          return newSet;
        });
        
        // Remove from recently uploaded set (they've been processed now)
        setRecentlyUploadedImageIds(prev => {
          const newSet = new Set(prev);
          newlyProcessedIds.forEach(id => newSet.delete(id));
          return newSet;
        });
      });
    }
    
    // When run completes or is cancelled, trigger final flash and remove green hue
    if ((currentStatus === 'completed' || currentStatus === 'cancelled') && previousRunStatus && (previousRunStatus === 'running' || previousRunStatus === 'pending')) {
      // Get ALL images that were processed in this run
      const processedInRun = getProcessedImageIds(batchData.images);
      
      if (processedInRun.length > 0) {
        startTransition(() => {
          // Trigger final flash animation for all processed images
          setFlashingImageIds(new Set(processedInRun));
        });
      }
    }
    
    // Update previous image results for next comparison
    previousImageResultsRef.current = currentImageResults;
    
    // Update previous run info when status changes
    if (currentStatus) {
      startTransition(() => {
        setPreviousRunStatus(currentStatus);
        // Update previous model and threshold when run completes or is cancelled
        if ((currentStatus === 'completed' || currentStatus === 'cancelled') && latestModelId !== null && latestThreshold !== null) {
          setPreviousRunModelId(latestModelId);
          setPreviousRunThreshold(latestThreshold);
        }
      });
    }
  }, [
    batchData?.latest_run?.status,
    batchData?.latest_run?.run_id,
    batchData?.latest_run?.model_id,
    batchData?.latest_run?.threshold,
    batchData?.images,
    previousRunStatus,
    previousRunModelId,
    previousRunThreshold,
    recentlyUploadedImageIds,
    flashedImageIds,
    greenHueImageIds,
    setRecentlyUploadedImageIds
  ]);

  // Clear flash after 1 second using useEffect with cleanup
  useEffect(() => {
    if (flashingImageIds.size > 0) {
      const timeoutId = setTimeout(() => {
        startTransition(() => {
          setFlashingImageIds(new Set());
        });
      }, 1000);
      
      return () => clearTimeout(timeoutId);
    }
  }, [flashingImageIds]);

  // Remove green hue when run completes (after flash)
  useEffect(() => {
    const currentStatus = batchData?.latest_run?.status;
    if (currentStatus === 'completed' && flashingImageIds.size === 0 && greenHueImageIds.size > 0) {
      const timeoutId = setTimeout(() => {
        startTransition(() => {
          setGreenHueImageIds(new Set());
        });
      }, 100);
      
      return () => clearTimeout(timeoutId);
    }
  }, [batchData?.latest_run?.status, flashingImageIds.size, greenHueImageIds.size]);

  return {
    flashingImageIds,
    greenHueImageIds,
  };
}

