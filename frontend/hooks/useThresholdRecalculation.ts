import { useState, useEffect, useRef } from 'react';
import { recalculateThreshold } from '@/lib/api';

interface RecalculatedCounts {
  live_count: number;
  dead_count: number;
}

interface RecalculationResult {
  images: Record<number, RecalculatedCounts>;
  totals: {
    live_total: number;
    dead_total: number;
  };
  run_id: number | null;
}

export function useThresholdRecalculation(
  collectionId: number | null,
  threshold: number,
  selectedModelId: number | null,
  latestRunThreshold?: number,
  latestRunModelId?: number,
  isRunning?: boolean
) {
  const [recalculatedData, setRecalculatedData] = useState<RecalculationResult | null>(null);
  const [isRecalculating, setIsRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Clear previous debounce timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Don't recalculate if:
    // - No collection ID
    // - No model selected
    // - Currently running a new run
    // - No threshold difference from latest run (and same model)
    if (
      !collectionId ||
      !selectedModelId ||
      isRunning ||
      (threshold === latestRunThreshold && selectedModelId === latestRunModelId)
    ) {
      setRecalculatedData(null);
      return;
    }

    // Debounce threshold changes (300ms)
    debounceTimer.current = setTimeout(async () => {
      try {
        setIsRecalculating(true);
        setError(null);

        const result = await recalculateThreshold(
          collectionId,
          threshold,
          selectedModelId
        );

        // Only set recalculated data if we got valid results
        if (result.run_id !== null) {
          setRecalculatedData(result);
        } else {
          // No run exists for this model yet
          setRecalculatedData(null);
        }
      } catch (err) {
        console.error('Failed to recalculate threshold:', err);
        setError(err instanceof Error ? err.message : 'Failed to recalculate');
        setRecalculatedData(null);
      } finally {
        setIsRecalculating(false);
      }
    }, 300);

    // Cleanup on unmount
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [collectionId, threshold, selectedModelId, latestRunThreshold, latestRunModelId, isRunning]);

  return {
    recalculatedImages: recalculatedData?.images || {},
    recalculatedTotals: recalculatedData?.totals || null,
    isRecalculating,
    error,
    hasRecalculatedData: recalculatedData !== null,
  };
}
