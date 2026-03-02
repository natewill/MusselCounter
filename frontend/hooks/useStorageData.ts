import { useState, useEffect, useRef } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';

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
          
          const message = `${count} image${count === 1 ? '' : 's'} added${dupCount > 0 ? `, ${dupCount} duplicate${dupCount === 1 ? '' : 's'} skipped` : ''}!`;
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
      
      // For current session only; no persistence across reloads
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
