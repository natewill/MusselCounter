import { useState, useEffect, startTransition } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getBatch, getRun } from '@/lib/api';
import { safeGetNumber, safeSetItem } from '@/utils/storage';

export function useBatchData(runId: number) {
  const [batchId, setBatchId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.5);

  // Initial load - get batch_id from run or use runId as batchId
  useEffect(() => {
    const loadRunData = async () => {
      try {
        // Try to get batch_id from localStorage first (faster)
        const storedBatchId = await safeGetNumber('currentBatchId');
        if (storedBatchId) {
          setBatchId(storedBatchId);
        } else {
          // If not in localStorage, try to get it from the run API
          try {
            const runData = await getRun(runId);
            if (runData && runData.batch_id) {
              setBatchId(runData.batch_id);
              await safeSetItem('currentBatchId', runData.batch_id.toString());
            } else {
              setError('Run not found. Please upload images from the home page.');
              setLoading(false);
            }
          } catch {
            // If getRun fails, assume runId is actually a batchId (new flow from home)
            setBatchId(runId);
            await safeSetItem('currentBatchId', runId.toString());
          }
        }
      } catch (err) {
        console.error('Failed to load run data:', err);
        setError('Failed to load run data. Please try again.');
        setLoading(false);
      }
    };
    
    loadRunData();
  }, [runId]);

  // Use react-query for batch data fetching with automatic polling
  const {
    data: batchData,
    error: batchError,
    isLoading: batchLoading,
  } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => getBatch(batchId!),
    enabled: !!batchId,
    refetchInterval: (query) => {
      // Poll every 1 second if run is active
      const data = query.state.data;
      const runStatus = data?.latest_run?.status;
      if (runStatus === 'running' || runStatus === 'pending') {
        return 1000;
      }
      return false; // Don't poll if completed/failed
    },
    staleTime: 0,
    gcTime: 30000,
  });

  // Handle query success - clear error on successful data fetch
  useEffect(() => {
    if (batchData && !batchError) {
      startTransition(() => {
        setError(null);
      });
    }
  }, [batchData, batchError]);

  // Handle query error
  useEffect(() => {
    if (batchError) {
      startTransition(() => {
        setError((batchError as Error).message || 'Failed to load batch data');
        setLoading(false);
      });
    }
  }, [batchError]);

  // Update loading state based on batch query
  useEffect(() => {
    if (batchId) {
      if (!batchLoading && batchData) {
        startTransition(() => {
          setLoading(false);
        });
      }
    }
  }, [batchId, batchLoading, batchData]);

  // Handle URL updates when batch data changes
  useEffect(() => {
    if (batchData) {
      if (batchData.latest_run && batchData.latest_run.run_id !== runId) {
        window.history.replaceState(null, '', `/run/${batchData.latest_run.run_id}`);
      }
    }
  }, [batchData, runId]);

  // Update threshold when batch data changes
  useEffect(() => {
    if (batchData?.latest_run?.threshold !== null && batchData?.latest_run?.threshold !== undefined) {
      startTransition(() => {
        setThreshold(batchData.latest_run.threshold);
      });
    }
  }, [batchData?.latest_run?.threshold]);

  // Compute derived values
  const batch = batchData?.batch || { name: 'Loading...', live_mussel_count: 0 };
  const images = batchData?.images || [];
  const latestRun = batchData?.latest_run || null;
  const isRunning = latestRun && (latestRun.status === 'pending' || latestRun.status === 'running');

  return { 
    batchId, 
    batchData, 
    batch,
    images,
    latestRun,
    isRunning,
    threshold,
    setThreshold,
    loading, 
    error, 
    setError, 
    setLoading 
  };
}

