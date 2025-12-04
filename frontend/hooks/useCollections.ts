import { useQuery } from '@tanstack/react-query';
import { getCollections } from '@/lib/api';

export interface CollectionSummary {
  collection_id: number;
  name: string | null;
  description: string | null;
  image_count: number;
  live_mussel_count?: number;
  created_at: string;
  updated_at?: string;
  first_image_path?: string | null;
}

export function useCollections() {
  const query = useQuery<CollectionSummary[]>({
    queryKey: ['collections'],
    queryFn: () => getCollections(),
    staleTime: 30_000,
  });

  return {
    collections: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as Error | null,
    refetch: query.refetch,
  };
}
