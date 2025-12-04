import { useMemo } from 'react';
import Link from 'next/link';

export default function ImageList({ images, onDeleteImage, deletingImageId, selectedModelId, flashingImageIds, greenHueImageIds, isRunning, currentThreshold, latestRun, recalculatedImages, sortBy, onSortChange, collectionId }) {
  // Sort images based on sortBy prop or green hue during runs
  const sortedImages = useMemo(() => {
    let sorted = [...images];

    // Apply user-selected sort if provided
    if (sortBy === 'live_count') {
      sorted.sort((a, b) => {
        const aCount = recalculatedImages?.[a.image_id]?.live_mussel_count ?? a.live_mussel_count ?? 0;
        const bCount = recalculatedImages?.[b.image_id]?.live_mussel_count ?? b.live_mussel_count ?? 0;
        return bCount - aCount; // Descending order (highest first)
      });
    } else if (sortBy === 'name') {
      sorted.sort((a, b) => {
        const aName = a.filename || '';
        const bName = b.filename || '';
        return aName.localeCompare(bName);
      });
    }

    // During a run, prioritize green hue images if no explicit sort is set
    if (!sortBy && isRunning && greenHueImageIds && greenHueImageIds.size > 0) {
      sorted.sort((a, b) => {
        const aHasGreenHue = greenHueImageIds.has(a.image_id);
        const bHasGreenHue = greenHueImageIds.has(b.image_id);

        // Images with green hue come first
        if (aHasGreenHue && !bHasGreenHue) return -1;
        if (!aHasGreenHue && bHasGreenHue) return 1;

        return 0;
      });
    }

    return sorted;
  }, [images, greenHueImageIds, isRunning, sortBy, recalculatedImages]);

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
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Images ({images.length})
        </h2>
        <div className="flex items-center gap-3">
          <label htmlFor="sort-select" className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Sort by:
          </label>
          <select
            id="sort-select"
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value)}
            className="px-3 py-1.5 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Default</option>
            <option value="live_count">Live Mussel Count</option>
            <option value="name">File Name</option>
          </select>
        </div>
      </div>
      {sortedImages.length === 0 ? (
        <div className="text-zinc-600 dark:text-zinc-400">No images in this collection yet.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedImages.map((image) => {
            // Check if image has been processed with the selected model
            const processedModelIds = image.processed_model_ids || [];
            const isProcessedWithSelectedModel = selectedModelId && processedModelIds.includes(selectedModelId);
            
            // Check if image has results for the CURRENT model+threshold combination
            // An image may have results from YOLO at 0.47, but not from RCNN at 0.47
            const hasResults = (image.live_mussel_count !== null && image.live_mussel_count !== undefined) ||
                              (image.dead_mussel_count !== null && image.dead_mussel_count !== undefined) ||
                              image.processed_at;
            
            // Check if results are valid for CURRENT model
            // With threshold recalculation, we only need to check if processed with selected model
            // Threshold changes no longer require re-running the model
            const hasValidResults = hasResults && isProcessedWithSelectedModel;
            
            // Check if this image should flash green (final flash on completion)
            const isFlashing = flashingImageIds && flashingImageIds.has(image.image_id);
            // Check if this image should have persistent green hue (during run only)
            // Show green hue for images in greenHueImageIds (processed in current run, including with new threshold) AND run is active
            const hasGreenHue = isRunning && (greenHueImageIds && greenHueImageIds.has(image.image_id));
            
            // Show orange hue if a model is selected AND image doesn't have green hue AND doesn't have valid results
            // Valid results = processed with current model + current threshold
            // This means changing models or thresholds will bring back the orange hue
            const needsProcessing = selectedModelId && !hasGreenHue && !hasValidResults;
            
            // Extract filename from stored_path for thumbnail URL
            // stored_path format: "data/uploads/{hash}_{filename}"
            const thumbnailUrl = image.stored_path
              ? `http://127.0.0.1:8000/uploads/${image.stored_path.split('/').pop()}`
              : null;
            
            // Always allow navigation; edit mode can be disabled downstream if no results
            const modelIdForLink = selectedModelId ?? latestRun?.model_id ?? null;
            const collectionIdForLink = collectionId ?? latestRun?.collection_id ?? null;
            const sortParam = sortBy || null;
            
            return (
              <Link
                key={image.image_id}
                id={`image-card-${image.image_id}`}
                href={modelIdForLink && collectionIdForLink ? `/edit/${image.image_id}?modelId=${modelIdForLink}&collectionId=${collectionIdForLink}${sortParam ? `&sort=${encodeURIComponent(sortParam)}` : ''}` : '#'}
                className={`block border rounded-lg overflow-hidden hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors relative ${
                  isFlashing
                    ? 'green-flash'
                    : hasGreenHue
                    ? 'green-hue'
                    : needsProcessing
                    ? 'border-amber-300 dark:border-amber-700 bg-amber-50/20 dark:bg-amber-900/15 ring-2 ring-amber-300/20 dark:ring-amber-700/20'
                    : 'border-zinc-200 dark:border-zinc-800'
                } ${!modelIdForLink || !collectionIdForLink ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
                onClick={(e) => {
                  // Prevent navigation if no model/collection available
                  if (!modelIdForLink || !collectionIdForLink) {
                    e.preventDefault();
                  }
                }}
              >
                {onDeleteImage && (
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      if (!isRunning) {
                        onDeleteImage(image.image_id);
                      }
                    }}
                    disabled={isRunning || deletingImageId === image.image_id}
                    className={`absolute top-2 right-2 p-1 bg-white/90 dark:bg-zinc-800/90 backdrop-blur-sm rounded z-10 ${
                      isRunning || deletingImageId === image.image_id
                        ? 'text-zinc-400 dark:text-zinc-600 cursor-not-allowed opacity-50'
                        : 'text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300'
                    }`}
                    title={isRunning ? "Cannot delete images while a run is in progress" : "Remove image from collection"}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
                
                {/* Image Thumbnail */}
                {thumbnailUrl && (
                  <div className="relative w-full h-48 bg-zinc-100 dark:bg-zinc-800">
                    <img 
                      src={thumbnailUrl} 
                      alt={image.filename}
                      className="w-full h-full object-cover"
                      loading="lazy"
                      onError={(e) => {
                        // Fallback if image fails to load
                        e.target.style.display = 'none';
                        e.target.nextElementSibling.style.display = 'flex';
                      }}
                    />
                    {/* Fallback placeholder */}
                    <div className="absolute inset-0 hidden items-center justify-center text-zinc-400 dark:text-zinc-600">
                      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                  </div>
                )}
                
                {/* Image Info */}
                <div className="p-4">
                  <div className="font-medium text-zinc-900 dark:text-zinc-100 mb-2 truncate text-sm">
                    {image.filename}
                  </div>
                  <div className="flex gap-4 text-sm">
                    <div>
                      <span className="text-zinc-600 dark:text-zinc-400">Live: </span>
                      <span className="font-medium text-green-600 dark:text-green-400">
                        {recalculatedImages && recalculatedImages[image.image_id]
                          ? recalculatedImages[image.image_id].live_count
                          : (image.live_mussel_count || 0)}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-600 dark:text-zinc-400">Dead: </span>
                      <span className="font-medium text-red-600 dark:text-red-400">
                        {recalculatedImages && recalculatedImages[image.image_id]
                          ? recalculatedImages[image.image_id].dead_count
                          : (image.dead_mussel_count || 0)}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
      </div>
    </>
  );
}
