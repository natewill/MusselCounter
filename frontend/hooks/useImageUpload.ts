import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadImagesToCollection } from '@/lib/api';
import { validateImageFiles } from '@/utils/validation';
import { filterNonDuplicateIds } from '@/utils/imageUtils';
import { invalidateCollectionQuery } from '@/utils/queryUtils';
import { formatUploadSuccessMessage } from '@/utils/messageUtils';

export function useImageUpload(
  collectionId: number | null,
  setError: (error: string | null) => void,
  setLoading: (loading: boolean) => void,
  setRecentlyUploadedImageIds: (ids: Set<number> | ((prev: Set<number>) => Set<number>)) => void,
  setSuccessMessage: (message: string | null) => void
) {
  const [uploading, setUploading] = useState(false);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: ({ collectionId, files }: { collectionId: number; files: File[] }) =>
      uploadImagesToCollection(collectionId, files),
    onSuccess: async (result) => {
      const addedCount = result.added_count || 0;
      const duplicateCount = result.duplicate_count || 0;
      const uploadedImageIds = result.image_ids || [];
      const duplicateImageIds = result.duplicate_image_ids || [];
      
      // Track recently uploaded image IDs (exclude duplicates)
      const nonDuplicateIds = filterNonDuplicateIds(uploadedImageIds, duplicateImageIds);
      setRecentlyUploadedImageIds(new Set(nonDuplicateIds));
      
      // Set success message immediately
      const message = formatUploadSuccessMessage(addedCount, duplicateCount);
      setSuccessMessage(message);
      
      // Invalidate and refetch collection data
      invalidateCollectionQuery(queryClient, collectionId);
      
      setLoading(false);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to add images');
      setLoading(false);
    },
  });

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const { validFiles: imageFiles, errors: validationErrors } = validateImageFiles(files);
    
    if (imageFiles.length === 0) {
      if (validationErrors.length > 0) {
        setError(validationErrors.join(' '));
      } else {
        setError('Please select valid image files');
      }
      return;
    }
    
    // Show warnings for invalid files but continue with valid ones
    if (validationErrors.length > 0) {
      console.warn('Some files were skipped:', validationErrors);
    }

    if (!collectionId) {
      setError('No collection available. Please refresh the page.');
      return;
    }

    setUploading(true);
    setError(null);

    uploadMutation.mutate(
      { collectionId, files: imageFiles },
      {
        onSettled: () => {
          setUploading(false);
        },
      }
    );
  };

  return { uploading, handleFileInputChange };
}

