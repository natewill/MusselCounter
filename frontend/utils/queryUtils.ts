import { QueryClient } from '@tanstack/react-query';

/**
 * Invalidate collection query to trigger refetch
 * @param queryClient - React Query client instance
 * @param collectionId - Collection ID to invalidate
 */
export function invalidateCollectionQuery(queryClient: QueryClient, collectionId: number | null): void {
  if (collectionId) {
    queryClient.invalidateQueries({ queryKey: ['collection', collectionId] });
  }
}

