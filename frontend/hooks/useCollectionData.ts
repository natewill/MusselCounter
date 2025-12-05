import { useState, useEffect, startTransition } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCollection } from '@/lib/api';

export function useCollectionData(collectionIdParam: number, selectedModelId?: number | null) {
  const [collectionId, setCollectionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.5);

  // Initial load - use the collectionId from URL parameter only
  useEffect(() => {
    setCollectionId(collectionIdParam);
  }, [collectionIdParam]);

  // Use react-query for collection data fetching with automatic polling
  const {
    data: collectionData,
    error: collectionError,
    isLoading: collectionLoading,
    refetch,
  } = useQuery({
    queryKey: ['collection', collectionId, selectedModelId],
    queryFn: () => getCollection(collectionId!, selectedModelId ?? undefined),
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

  // Update threshold when latest run changes
  useEffect(() => {
    if (collectionData?.latest_run?.threshold !== null && collectionData?.latest_run?.threshold !== undefined) {
      startTransition(() => {
        setThreshold(collectionData.latest_run.threshold);
      });
    }
  }, [collectionData?.latest_run?.threshold]);

  // Derive helper structures
  const collectionInfo = collectionData?.collection || {
    name: 'Loading...',
    live_mussel_count: 0,
    dead_mussel_count: 0,
  };

  const collection = {
    ...collectionInfo,
    collection_id: collectionInfo?.collection_id ?? collectionId,
  };

  const images = collectionData?.images || [];
  const latestRun = collectionData?.latest_run || null;
  const isRunning = latestRun && (latestRun.status === 'pending' || latestRun.status === 'running');
  const serverTime = collectionData?.server_time ?? null;

  return {
    collectionId,
    collectionData: collectionData ? { ...collectionData, collection } : null,
    collection,
    images,
    latestRun,
    isRunning,
    serverTime,
    threshold,
    setThreshold,
    loading,
    error,
    setError,
    setLoading,
    refetch,
  };
}
