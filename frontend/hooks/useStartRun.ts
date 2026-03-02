import { useRef, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { startRun } from '@/lib/api';

export function useStartRun(
  collectionId: number,
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
    if (!selectedModelId) {
      setError('Please select a model before starting a run.');
      return;
    }
    
    // Prevent double-clicks
    if (loading) {
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      await startRun(collectionId, selectedModelId, threshold);

      // Invalidate and refetch collection data to show the new run
      queryClient.invalidateQueries({ queryKey: ['collection', collectionId] });
      
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
