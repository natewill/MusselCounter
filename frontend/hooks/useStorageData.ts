import { useState, useEffect, useRef } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { safeRemoveItem, safeGetJSON } from '@/utils/storage';
import { formatUploadSuccessMessage } from '@/utils/messageUtils';

export function useStorageData() {
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [recentlyUploadedImageIds, setRecentlyUploadedImageIds] = useState<Set<number>>(new Set());
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const processedParamsRef = useRef(false);

  useEffect(() => {
    const loadStorageData = async () => {
      // Only process query params once on mount
      if (!processedParamsRef.current) {
        processedParamsRef.current = true;
        
        // Read upload counts from URL query params instead of localStorage
        const addedCount = searchParams.get('added');
        const duplicateCount = searchParams.get('duplicates');
        
        if (addedCount) {
          const count = Number(addedCount);
          const dupCount = duplicateCount ? Number(duplicateCount) : 0;
          
          const message = formatUploadSuccessMessage(count, dupCount);
          setSuccessMessage(message);
          
          // Remove query params from URL after reading them
          const params = new URLSearchParams(searchParams.toString());
          params.delete('added');
          params.delete('duplicates');
          const newQuery = params.toString();
          const newUrl = newQuery ? `${pathname}?${newQuery}` : pathname;
          router.replace(newUrl, { scroll: false });
        }
      }
      
      // Load recently uploaded image IDs from localStorage (still needed for flashing)
      // This should only run once on mount
      const recentlyUploadedIds = await safeGetJSON('recentlyUploadedImageIds');
      if (recentlyUploadedIds && Array.isArray(recentlyUploadedIds)) {
        await safeRemoveItem('recentlyUploadedImageIds');
        setRecentlyUploadedImageIds(new Set(recentlyUploadedIds));
      }
    };
    
    loadStorageData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

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

