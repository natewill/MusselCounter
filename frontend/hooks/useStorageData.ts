import { useState, useEffect } from 'react';
import { safeGetItem, safeRemoveItem, safeGetJSON } from '@/utils/storage';
import { formatUploadSuccessMessage } from '@/utils/messageUtils';

export function useStorageData() {
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [recentlyUploadedImageIds, setRecentlyUploadedImageIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    const loadStorageData = async () => {
      const uploadCount = await safeGetItem('uploadedImageCount');
      const duplicateCount = await safeGetItem('duplicateImageCount');
      const recentlyUploadedIds = await safeGetJSON('recentlyUploadedImageIds');
      
      if (uploadCount) {
        const count = Number(uploadCount);
        const dupCount = duplicateCount ? Number(duplicateCount) : 0;
        
        const message = formatUploadSuccessMessage(count, dupCount);
        setSuccessMessage(message);
        await safeRemoveItem('uploadedImageCount');
        await safeRemoveItem('duplicateImageCount');
      }
      
      // Load recently uploaded image IDs from localStorage
      if (recentlyUploadedIds && Array.isArray(recentlyUploadedIds)) {
        await safeRemoveItem('recentlyUploadedImageIds');
        setRecentlyUploadedImageIds(new Set(recentlyUploadedIds));
      }
    };
    
    loadStorageData();
  }, []);

  // Auto-clear success message after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timeoutId = setTimeout(() => {
        setSuccessMessage(null);
      }, 5000);
      
      return () => clearTimeout(timeoutId);
    }
  }, [successMessage]);

  return { successMessage, setSuccessMessage, recentlyUploadedImageIds, setRecentlyUploadedImageIds };
}

