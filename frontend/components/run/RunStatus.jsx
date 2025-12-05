export default function RunStatus({ latestRun, isRunning, images, onStopRun, stopping }) {
  // Calculate values first for logging and use later
  // Use processed_count from run table for accurate real-time progress (updated as batches complete)
  // Fall back to counting images with counts if processed_count not available
  const totalImagesCalc = latestRun?.total_images > 0 
    ? latestRun.total_images 
    : (images ? images.length : 0);
  const processedImagesCalc = latestRun?.processed_count !== undefined && latestRun?.processed_count !== null
    ? latestRun.processed_count  // Use run.processed_count for real-time progress
    : (images ? images.filter(img => 
        img.live_mussel_count !== null || 
        img.dead_mussel_count !== null || 
        img.error_msg !== null
      ).length : 0);
  const progressCalc = totalImagesCalc > 0 ? (processedImagesCalc / totalImagesCalc) * 100 : 0;
  
  // Show ready state if we don't have run data yet but we have images
  if (!latestRun) {
    // If we have images but no run, show ready state
    if (images && images.length > 0) {
      return (
        <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800 h-full">
          <h2 className="text-xl font-semibold mb-4 text-zinc-900 dark:text-zinc-100">Current Run</h2>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Status:</span>
              <span className="px-3 py-1 rounded text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                Ready
              </span>
            </div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-2">
              {images.length} {images.length === 1 ? 'image' : 'images'} ready to process
            </div>
            <div className="text-sm text-zinc-500 dark:text-zinc-500 italic mt-2">
              Click &quot;Start New Run&quot; to begin processing
            </div>
          </div>
        </div>
      );
    }
    return null;
  }

  // Use the calculated values from above
  const totalImages = totalImagesCalc;
  const processedImages = processedImagesCalc;
  const progress = progressCalc;

  const parseDate = (value) => {
    if (!value) return null;
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed;
    }
    // If timestamp is missing timezone information, assume UTC
    return new Date(`${value}Z`);
  };

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800 h-full">
      <h2 className="text-xl font-semibold mb-4 text-zinc-900 dark:text-zinc-100">Current Run</h2>
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-600 dark:text-zinc-400">Status:</span>
          <span className={`px-3 py-1 rounded text-sm font-medium ${
            latestRun.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
            latestRun.status === 'running' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
            latestRun.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
            'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
          }`}>
            {latestRun.status}
          </span>
        </div>

        {/* Progress Bar - Show when running or pending */}
        {(isRunning || latestRun.status === 'pending') && (
          <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="text-zinc-600 dark:text-zinc-400 font-medium">
                Processing Images
              </span>
              {totalImages > 0 ? (
                <span className="text-zinc-600 dark:text-zinc-400">
                  {processedImages} / {totalImages} ({progress.toFixed(0)}%)
                </span>
              ) : (
                <span className="text-zinc-600 dark:text-zinc-400">
                  Starting...
                </span>
              )}
            </div>
            <div className="w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-4 overflow-hidden relative">
              {totalImages > 0 ? (
                <>
                  <div
                    className="bg-blue-600 h-4 rounded-full transition-all duration-500 ease-out relative"
                    style={{ width: `${Math.max(progress, 5)}%` }}
                  >
                    <div className="absolute inset-0 bg-blue-400 animate-pulse" />
                  </div>
                  {/* Animated shimmer effect */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
                </>
              ) : (
                <div className="bg-blue-600 h-4 rounded-full animate-pulse" style={{ width: '100%' }} />
              )}
            </div>
            {totalImages > 0 && processedImages < totalImages && (
              <div className="text-xs text-zinc-500 dark:text-zinc-500 text-center">
                {totalImages - processedImages} images remaining
              </div>
            )}
          </div>
        )}

        {/* Stop button for running runs */}
        {(latestRun.status === 'running' || latestRun.status === 'pending') && onStopRun && (
          <button
            onClick={() => onStopRun(latestRun.run_id)}
            disabled={stopping}
            className="w-full mt-2 px-4 py-2 bg-zinc-600 hover:bg-zinc-700 disabled:bg-zinc-400 dark:bg-zinc-700 dark:hover:bg-zinc-600 text-white rounded-lg transition-colors text-sm font-medium"
          >
            {stopping ? 'Stopping...' : 'Stop Run'}
          </button>
        )}

        {latestRun.status === 'completed' && totalImages > 0 && (
          <div className="text-sm text-green-600 dark:text-green-400">
            ✓ Completed: {processedImages} / {totalImages} images processed
          </div>
        )}
        
        {latestRun.status === 'cancelled' && (
          <div className="text-sm text-yellow-600 dark:text-yellow-400">
            ⚠ Run was cancelled
          </div>
        )}

        {latestRun.started_at && (
          <div className="text-sm text-zinc-600 dark:text-zinc-400">
            Started: {(() => {
              const parsed = parseDate(latestRun.started_at);
              return parsed && !Number.isNaN(parsed.getTime()) ? parsed.toLocaleString() : '—';
            })()}
          </div>
        )}
        {latestRun.finished_at && (
          <div className="text-sm text-zinc-600 dark:text-zinc-400">
            Finished: {(() => {
              const parsed = parseDate(latestRun.finished_at);
              return parsed && !Number.isNaN(parsed.getTime()) ? parsed.toLocaleString() : '—';
            })()}
          </div>
        )}
      </div>
    </div>
  );
}
