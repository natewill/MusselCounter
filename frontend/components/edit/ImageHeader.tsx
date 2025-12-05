'use client';

import Link from 'next/link';

interface ImageHeaderProps {
  filename: string;
  collectionId: number;
  imageId: number;
  modelId?: number | null;
  hasResults?: boolean;
  sortBy?: string;
  isEditMode: boolean;
  onToggleEditMode: () => void;
  visiblePolygons: boolean;
  onToggleVisiblePolygons: () => void;
}

export default function ImageHeader({
  filename,
  collectionId,
  imageId,
  modelId,
  sortBy,
  hasResults = true,
  isEditMode,
  onToggleEditMode,
  visiblePolygons,
  onToggleVisiblePolygons,
}: ImageHeaderProps) {
  const backUrlBase = modelId
    ? `/collection/${collectionId}?modelId=${modelId}`
    : `/collection/${collectionId}`;
  const backUrl = sortBy
    ? `${backUrlBase}&sort=${encodeURIComponent(sortBy)}#image-card-${imageId}`
    : `${backUrlBase}#image-card-${imageId}`;

  return (
    <div className="mb-6">
      <Link
        href={backUrl}
        className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-2 mb-4"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to collection
      </Link>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{filename}</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={hasResults ? onToggleEditMode : undefined}
            disabled={!hasResults}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              !hasResults
                ? 'bg-zinc-200 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-500 cursor-not-allowed opacity-60'
                : isEditMode
                ? 'bg-green-600 dark:bg-green-500 text-white hover:bg-green-700 dark:hover:bg-green-600'
                : 'bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-300 dark:hover:bg-zinc-600'
            }`}
            title={!hasResults ? 'Run this image to enable editing' : undefined}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            {isEditMode ? 'Exit Edit Mode' : 'Edit Image'}
          </button>
          <button
            onClick={onToggleVisiblePolygons}
            className="px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 text-zinc-900 dark:text-zinc-100"
            title={visiblePolygons ? 'Hide Boxes' : 'Show Boxes'}
          >
            {visiblePolygons ? (
              <>
                <span>Bounding Boxes Visible</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </>
            ) : (
              <>
                <span>Bounding Boxes Hidden</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                </svg>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
