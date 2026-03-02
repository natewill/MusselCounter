import { useState, useEffect, startTransition } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCollection } from '@/lib/api';

export function useCollectionData(collectionIdParam: number, selectedModelId?: number | null) {
  const [threshold, setThreshold] = useState(0.5);
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  // Use react-query for collection data fetching with automatic polling
  const {
    data: queryData,
    error: queryError,
    isLoading: queryLoading,
    refetch,
  } = useQuery({
    queryKey: ['collection', collectionIdParam, selectedModelId],
    queryFn: () => getCollection(collectionIdParam, selectedModelId ?? undefined),
    enabled: collectionIdParam > 0,
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

  // Update threshold when latest run changes
  useEffect(() => {
    if (queryData?.latest_run?.threshold !== null && queryData?.latest_run?.threshold !== undefined) {
      startTransition(() => {
        setThreshold(queryData.latest_run.threshold);
      });
    }
  }, [queryData?.latest_run?.threshold]);

  // Derive helper structures
  const collectionInfo = queryData?.collection || {
    name: 'Loading...',
    live_mussel_count: 0,
    dead_mussel_count: 0,
  };

  const collection = {
    ...collectionInfo,
    collection_id: collectionInfo?.collection_id ?? collectionIdParam,
  };

  const images = queryData?.images || [];
  const latestRun = queryData?.latest_run || null;
  const isRunning = latestRun && (latestRun.status === 'pending' || latestRun.status === 'running');
  const loading = manualLoading || queryLoading;
  const queryErrorMessage = queryError ? (queryError as Error).message || 'Failed to load collection data' : null;
  const error = manualError || queryErrorMessage;

  return {
    collectionId: collectionIdParam,
    collectionData: queryData ? { ...queryData, collection } : null,
    collection,
    images,
    latestRun,
    isRunning,
    threshold,
    setThreshold,
    loading,
    error,
    setError: setManualError,
    setLoading: setManualLoading,
    refetch,
  };
}
