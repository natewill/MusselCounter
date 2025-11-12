import { useState, useEffect, startTransition } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCollection, getRun } from '@/lib/api';
import { safeGetNumber, safeSetItem } from '@/utils/storage';

export function useBatchData(runId: number) {
  const [collectionId, setCollectionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.5);

  // Initial load - get collection_id from run or storage
  useEffect(() => {
    const loadRunData = async () => {
      try {
        // Prefer cached collection id
        const storedCollectionId = await safeGetNumber('currentCollectionId');
        if (storedCollectionId) {
          setCollectionId(storedCollectionId);
          return;
        }

        // Fallback to legacy key for backwards compatibility
        const legacyBatchId = await safeGetNumber('currentBatchId');
        if (legacyBatchId) {
          setCollectionId(legacyBatchId);
          await safeSetItem('currentCollectionId', legacyBatchId.toString());
          return;
        }

        // Otherwise fetch run details to determine collection id
        try {
          const runData = await getRun(runId);
          if (runData && runData.collection_id) {
            setCollectionId(runData.collection_id);
            await safeSetItem('currentCollectionId', runData.collection_id.toString());
            await safeSetItem('currentBatchId', runData.collection_id.toString());
          } else {
            setError('Run not found. Please upload images from the home page.');
            setLoading(false);
          }
        } catch {
          // If getRun fails, assume runId is actually a collectionId (new flow from home)
          setCollectionId(runId);
          await safeSetItem('currentCollectionId', runId.toString());
          await safeSetItem('currentBatchId', runId.toString());
        }
      } catch (err) {
        console.error('Failed to load run data:', err);
        setError('Failed to load collection data. Please try again.');
        setLoading(false);
      }
    };
    loadRunData();
  }, [runId]);

  // Use react-query for collection data fetching with automatic polling
  const {
    data: collectionData,
    error: collectionError,
    isLoading: collectionLoading,
  } = useQuery({
    queryKey: ['collection', collectionId],
    queryFn: () => getCollection(collectionId!),
    enabled: !!collectionId,
    refetchInterval: (query) => {
      const data = query.state.data as Awaited<ReturnType<typeof getCollection>> | undefined;
      const runStatus = data?.latest_run?.status;
      if (runStatus === 'running' || runStatus === 'pending') {
        return 1000;
      }
      return false;
    },
    staleTime: 0,
    gcTime: 30000,
  });

  // Clear error on successful fetch
  useEffect(() => {
    if (collectionData && !collectionError) {
      startTransition(() => {
        setError(null);
      });
    }
  }, [collectionData, collectionError]);

  // Handle query error
  useEffect(() => {
    if (collectionError) {
      startTransition(() => {
        setError((collectionError as Error).message || 'Failed to load collection data');
        setLoading(false);
      });
    }
  }, [collectionError]);

  // Update loading state based on query
  useEffect(() => {
    if (collectionId) {
      if (!collectionLoading && collectionData) {
        startTransition(() => {
          setLoading(false);
        });
      }
    }
  }, [collectionId, collectionLoading, collectionData]);

  // Handle URL updates when collection data changes
  useEffect(() => {
    if (collectionData?.latest_run && collectionData.latest_run.run_id !== runId) {
      window.history.replaceState(null, '', `/run/${collectionData.latest_run.run_id}`);
    }
  }, [collectionData?.latest_run, runId]);

  // Update threshold when latest run changes
  useEffect(() => {
    if (collectionData?.latest_run?.threshold !== null && collectionData?.latest_run?.threshold !== undefined) {
      startTransition(() => {
        setThreshold(collectionData.latest_run.threshold);
      });
    }
  }, [collectionData?.latest_run?.threshold]);

  // Derive helper structures for legacy components
  const collectionInfo = collectionData?.collection || {
    name: 'Loading...',
    live_mussel_count: 0,
    dead_mussel_count: 0,
  };

  const batch = {
    ...collectionInfo,
    batch_id: collectionInfo?.collection_id ?? collectionId,
  };

  const images = collectionData?.images || [];
  const latestRun = collectionData?.latest_run || null;
  const isRunning = latestRun && (latestRun.status === 'pending' || latestRun.status === 'running');

  return {
    batchId: collectionId,
    batchData: collectionData ? { ...collectionData, batch } : null,
    batch,
    images,
    latestRun,
    isRunning,
    threshold,
    setThreshold,
    loading,
    error,
    setError,
    setLoading,
  };
}

