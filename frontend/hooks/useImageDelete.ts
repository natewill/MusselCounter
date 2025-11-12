import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteImageFromBatch } from '@/lib/api';
import { invalidateBatchQuery } from '@/utils/queryUtils';

export function useImageDelete(
  batchId: number | null,
  setError: (error: string | null) => void
) {
  const [deletingImageId, setDeletingImageId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const deleteImageMutation = useMutation({
    mutationFn: ({ batchId, imageId }: { batchId: number; imageId: number }) =>
      deleteImageFromBatch(batchId, imageId),
    onSuccess: () => {
      invalidateBatchQuery(queryClient, batchId);
      setDeletingImageId(null);
    },
    onError: (err: Error) => {
      console.error('Failed to delete image:', err);
      setError(err.message || 'Failed to remove image from batch.');
      setDeletingImageId(null);
    },
  });

  const handleDeleteImage = async (imageId: number) => {
    if (!batchId) return;
    
    setDeletingImageId(imageId);
    setError(null);
    deleteImageMutation.mutate({ batchId, imageId });
  };

  return { deletingImageId, handleDeleteImage };
}

