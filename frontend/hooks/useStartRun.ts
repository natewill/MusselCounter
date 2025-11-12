import { useRef, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { startRun } from '@/lib/api';
import { invalidateCollectionQuery } from '@/utils/queryUtils';
import { getThresholdValidationError } from '@/utils/validation';

export function useStartRun(
  collectionId: number | null,
  selectedModelId: number | null,
  threshold: number,
  loading: boolean,
  setLoading: (loading: boolean) => void,
  setError: (error: string | null) => void
) {
  const queryClient = useQueryClient();
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const handleStartNewRun = async () => {
    if (!collectionId) {
      setError('No collection available to start a run.');
      return;
    }
    
    if (!selectedModelId) {
      setError('Please select a model before starting a run.');
      return;
    }
    
    // Validate threshold
    const thresholdError = getThresholdValidationError(threshold);
    if (thresholdError) {
      setError(thresholdError);
      return;
    }
    
    // Prevent double-clicks
    if (loading) {
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const runResponse = await startRun(collectionId, selectedModelId, threshold);
      
      window.history.replaceState(null, '', `/run/${runResponse.run_id}`);
      
      // Invalidate and refetch batch data to show the new run
      invalidateCollectionQuery(queryClient, collectionId);
      
      // Reset loading after run starts (the run will be processed in background)
      setLoading(false);
    } catch (err) {
      // Don't set error if component unmounted
      if (!isMountedRef.current) {
        return;
      }
      
      console.error('Failed to start new run:', err);
      setError((err as Error).message || 'Failed to start new run.');
      setLoading(false);
    }
  };

  return { handleStartNewRun };
}

