'use client';

import { useEffect } from 'react';
import { getDbVersion } from '@/lib/api';
import { safeGetItem, safeSetItem, safeClear } from '@/utils/storage';

const DB_VERSION_KEY = 'db_version';

/**
 * Component that checks database version on mount and clears localStorage
 * if the database was reset
 */
export default function DatabaseVersionChecker() {
  useEffect(() => {
    // Only run in browser
    if (typeof window === 'undefined') {
      return;
    }
    
    const checkDbVersion = async () => {
      try {
        // Get current database version from backend
        const { db_version } = await getDbVersion();
        
    
        if (!db_version) {
          // If no version returned, database might be in an inconsistent state
          // Clear localStorage to be safe
          console.warn('No database version returned, clearing localStorage');
          await safeClear();
          return;
        }
        
        // Get stored version from localStorage
        const storedVersion = await safeGetItem(DB_VERSION_KEY);
        
        if (storedVersion !== db_version) {
          // Database was reset or is different - clear all localStorage
          await safeClear();
          
          // Store the new version
          await safeSetItem(DB_VERSION_KEY, db_version);
        } else {
          // Versions match, ensure we have the version stored
          await safeSetItem(DB_VERSION_KEY, db_version);
        }
      } catch (error) {
        // If we can't reach the backend, don't clear localStorage
        // (might be offline or backend not running)
        console.warn('Failed to check database version:', error);
      }
    };
    
    checkDbVersion();
  }, []);
  
  // This component doesn't render anything
  return null;
}

