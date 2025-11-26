import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteImageFromCollection } from '@/lib/api';
import { invalidateCollectionQuery } from '@/utils/queryUtils';

export function useImageDelete(
  collectionId: number | null,
  setError: (error: string | null) => void,
  isRunning: boolean = false
) {
  const [deletingImageId, setDeletingImageId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const deleteImageMutation = useMutation({
    mutationFn: ({ collectionId, imageId }: { collectionId: number; imageId: number }) =>
      deleteImageFromCollection(collectionId, imageId),
    onSuccess: () => {
      invalidateCollectionQuery(queryClient, collectionId);
      setDeletingImageId(null);
    },
    onError: (err: Error) => {
      console.error('Failed to delete image:', err);
      setError(err.message || 'Failed to remove image from collection.');
      setDeletingImageId(null);
    },
  });

  const handleDeleteImage = async (imageId: number) => {
    if (!collectionId) return;
    if (isRunning) {
      setError('Cannot delete images while a run is in progress');
      return;
    }
    
    setDeletingImageId(imageId);
    setError(null);
    deleteImageMutation.mutate({ collectionId, imageId });
  };

  return { deletingImageId, handleDeleteImage };
}

