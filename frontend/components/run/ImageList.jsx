export default function ImageList({ images, onDeleteImage, deletingImageId, selectedModelId, flashingImageIds, greenHueImageIds, isRunning, currentThreshold }) {
  return (
    <>
      <style>{`
        @keyframes greenFlash {
          0% {
            background-color: rgba(34, 197, 94, 0.1);
            border-color: rgba(34, 197, 94, 0.4);
          }
          50% {
            background-color: rgba(34, 197, 94, 0.15);
            border-color: rgba(34, 197, 94, 0.6);
          }
          100% {
            background-color: transparent;
            border-color: transparent;
          }
        }
        .green-flash {
          animation: greenFlash 1s ease-out;
        }
        .green-hue {
          background-color: rgba(34, 197, 94, 0.15);
          border-color: rgba(34, 197, 94, 0.5);
        }
        @media (prefers-color-scheme: dark) {
          @keyframes greenFlash {
            0% {
              background-color: rgba(34, 197, 94, 0.08);
              border-color: rgba(34, 197, 94, 0.3);
            }
            50% {
              background-color: rgba(34, 197, 94, 0.12);
              border-color: rgba(34, 197, 94, 0.5);
            }
            100% {
              background-color: transparent;
              border-color: transparent;
            }
          }
          .green-hue {
            background-color: rgba(34, 197, 94, 0.12);
            border-color: rgba(34, 197, 94, 0.4);
          }
        }
      `}</style>
      <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800">
      <h2 className="text-xl font-semibold mb-4 text-zinc-900 dark:text-zinc-100">
        Images ({images.length})
      </h2>
      {images.length === 0 ? (
        <div className="text-zinc-600 dark:text-zinc-400">No images in this batch yet.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {images.map((image) => {
            // Check if image has been processed with the selected model
            const processedModelIds = image.processed_model_ids || [];
            const isProcessed = selectedModelId && processedModelIds.includes(selectedModelId);
            
            // Check if image has results (was processed) - if it has results, don't show orange hue
            const hasResults = (image.live_mussel_count !== null && image.live_mussel_count !== undefined) ||
                              (image.dead_mussel_count !== null && image.dead_mussel_count !== undefined) ||
                              image.processed_at;
            
            // Check if the image's result threshold matches the current threshold
            // If threshold changed, image needs to be reprocessed
            const resultThreshold = image.result_threshold;
            const thresholdMatches = resultThreshold === null || resultThreshold === undefined || 
                                    (currentThreshold !== null && currentThreshold !== undefined && 
                                     Math.abs(resultThreshold - currentThreshold) < 0.001); // Allow small floating point differences
            
            // Check if this image should flash green (final flash on completion)
            const isFlashing = flashingImageIds && flashingImageIds.has(image.image_id);
            // Check if this image should have persistent green hue (during run only)
            // Show green hue for images in greenHueImageIds (processed in current run, including with new threshold) AND run is active
            const hasGreenHue = isRunning && (greenHueImageIds && greenHueImageIds.has(image.image_id));
            
            // Only show orange hue if it needs processing AND doesn't have results yet AND doesn't have green hue
            // Also show orange if threshold changed (even if processed with same model) - needs reprocessing
            // Once it has results (even if not in processed_model_ids yet), remove the orange hue
            // Also don't show orange if it's in greenHueImageIds (to prevent delay)
            const needsProcessing = selectedModelId && !hasGreenHue && 
                                   ((!isProcessed && !hasResults) || (hasResults && !thresholdMatches));
            
            return (
              <div
                key={image.image_id}
                className={`border rounded-lg p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors relative ${
                  isFlashing
                    ? 'green-flash'
                    : hasGreenHue
                    ? 'green-hue'
                    : needsProcessing
                    ? 'border-amber-300 dark:border-amber-700 bg-amber-50/20 dark:bg-amber-900/15 ring-2 ring-amber-300/20 dark:ring-amber-700/20'
                    : 'border-zinc-200 dark:border-zinc-800'
                }`}
              >
                {onDeleteImage && (
                  <button
                    onClick={() => onDeleteImage(image.image_id)}
                    disabled={deletingImageId === image.image_id}
                    className="absolute top-2 right-2 p-1 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Remove image from batch"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
                <div className="font-medium text-zinc-900 dark:text-zinc-100 mb-2 truncate pr-6">
                  {image.filename}
                </div>
                <div className="flex gap-4 text-sm">
                  <div>
                    <span className="text-zinc-600 dark:text-zinc-400">Live: </span>
                    <span className="font-medium text-green-600 dark:text-green-400">
                      {image.live_mussel_count || 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-600 dark:text-zinc-400">Dead: </span>
                    <span className="font-medium text-red-600 dark:text-red-400">
                      {image.dead_mussel_count || 0}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      </div>
    </>
  );
}

