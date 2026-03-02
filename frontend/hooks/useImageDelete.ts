import { useState } from 'react';
import { deleteImageFromCollection } from '@/lib/api';

export function useImageDelete(
  collectionId: number,
  setError: (error: string | null) => void,
  isRunning: boolean = false
) {
  const [deletingImageId, setDeletingImageId] = useState<number | null>(null);

  const handleDeleteImage = async (imageId: number) => {
    if (isRunning) return;

    setDeletingImageId(imageId);
    setError(null);
    try {
      await deleteImageFromCollection(collectionId, imageId);
    } catch (err) {
      console.error('Failed to delete image:', err);
      setError((err as Error).message || 'Failed to remove image from collection.');
    } finally {
      setDeletingImageId(null);
    }
  };

  return { deletingImageId, handleDeleteImage };
}
