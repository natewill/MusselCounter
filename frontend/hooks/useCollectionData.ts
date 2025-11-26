import { useState, useEffect, startTransition } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCollection } from '@/lib/api';
import { safeGetNumber, safeSetItem } from '@/utils/storage';

export function useCollectionData(collectionIdParam: number, selectedModelId?: number | null) {
  const [collectionId, setCollectionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.5);

  // Initial load - get collection_id from storage or URL parameter
  useEffect(() => {
    const loadCollectionData = async () => {
      try {
        // Prefer cached collection id
        const storedCollectionId = await safeGetNumber('currentCollectionId');
        if (storedCollectionId) {
          setCollectionId(storedCollectionId);
          return;
        }

        // Use the collectionId from URL parameter
        setCollectionId(collectionIdParam);
        await safeSetItem('currentCollectionId', collectionIdParam.toString());
      } catch (err) {
        console.error('Failed to load collection data:', err);
        setError('Failed to load collection data. Please try again.');
        setLoading(false);
      }
    };
    loadCollectionData();
  }, [collectionIdParam]);

  // Use react-query for collection data fetching with automatic polling
  const {
    data: collectionData,
    error: collectionError,
    isLoading: collectionLoading,
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
  };
}

