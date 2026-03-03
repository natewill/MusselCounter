'use client';

import { useEffect, useState } from 'react';
import BoundingBoxesOverlay from './BoundingBoxesOverlay';

interface Polygon {
  bbox: number[];
  class: 'live' | 'dead';
  confidence: number;
}

interface ImageDisplayProps {
  imageUrl: string;
  filename: string;
  polygons: Polygon[];
  isEditMode: boolean;
  editingPolygonIndex: number | null;
  visiblePolygons: boolean;
  onFullscreen: () => void;
  onPolygonClick: (index: number) => void;
  onPolygonHover: (index: number | null) => void;
}

export default function ImageDisplay({
  imageUrl,
  filename,
  polygons,
  isEditMode,
  editingPolygonIndex,
  visiblePolygons,
  onFullscreen,
  onPolygonClick,
  onPolygonHover,
}: ImageDisplayProps) {
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    setNaturalSize({ width: 0, height: 0 });
  }, [imageUrl]);

  return (
    <div className="lg:col-span-2">
      <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
        {imageUrl && (
          <div className="max-h-[75vh] flex justify-center">
            <div className="relative inline-block max-w-full">
              <button
                onClick={onFullscreen}
                className="absolute top-2 right-2 p-2 bg-white/90 dark:bg-zinc-800/90 backdrop-blur-sm rounded text-zinc-700 dark:text-zinc-300 hover:bg-white dark:hover:bg-zinc-700 z-10 shadow-lg"
                title="Zoom to fullscreen"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
                </svg>
              </button>

              <img
                src={imageUrl}
                alt={filename}
                className="block h-auto max-h-[75vh] max-w-full rounded"
                onLoad={(e) =>
                  setNaturalSize({
                    width: e.currentTarget.naturalWidth || 0,
                    height: e.currentTarget.naturalHeight || 0,
                  })
                }
              />

              {visiblePolygons && (
                <BoundingBoxesOverlay
                  polygons={polygons}
                  imageWidth={naturalSize.width}
                  imageHeight={naturalSize.height}
                  isEditMode={isEditMode}
                  editingPolygonIndex={editingPolygonIndex}
                  onPolygonClick={onPolygonClick}
                  onPolygonHover={onPolygonHover}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
