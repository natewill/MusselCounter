import { useState } from 'react';
import { stopRun } from '@/lib/api';

export function useStopRun(
  setError: (error: string | null) => void,
  onSuccess?: () => void
) {
  const [stopping, setStopping] = useState(false);

  const handleStopRun = async (runId: number) => {
    if (!runId) {
      setError('No run ID provided');
      return;
    }

    if (stopping) {
      return; // Prevent double-clicks
    }

    try {
      setStopping(true);
      setError(null);
      
      await stopRun(runId);
      
      // Call success callback if provided (to refresh data)
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      console.error('Failed to stop run:', err);
      setError(err instanceof Error ? err.message : 'Failed to stop run');
    } finally {
      setStopping(false);
    }
  };

  return {
    stopping,
    handleStopRun,
  };
}

