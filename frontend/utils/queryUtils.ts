import { QueryClient } from '@tanstack/react-query';

/**
 * Invalidate batch query to trigger refetch
 * @param queryClient - React Query client instance
 * @param batchId - Batch ID to invalidate
 */
export function invalidateBatchQuery(queryClient: QueryClient, batchId: number | null): void {
  if (batchId) {
    queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
  }
}

