import { useState } from 'react';
import { deleteImageFromCollection } from '@/lib/api';

export function useImageDelete(
  collectionId: number | null,
  setError: (error: string | null) => void,
  isRunning: boolean = false,
  onDeleted?: () => Promise<unknown> | void
) {
  const [deletingImageId, setDeletingImageId] = useState<number | null>(null);

  const handleDeleteImage = async (imageId: number) => {
    if (!collectionId) return;
    if (isRunning) return;

    setDeletingImageId(imageId);
    setError(null);
    try {
      await deleteImageFromCollection(collectionId, imageId);
      if (onDeleted) {
        await onDeleted();
      }
    } catch (err) {
      console.error('Failed to delete image:', err);
      setError((err as Error).message || 'Failed to remove image from collection.');
    } finally {
      setDeletingImageId(null);
    }
  };

  return { deletingImageId, handleDeleteImage };
}
