'use client';

import { useRef } from 'react';
import BoundingBoxesOverlay from './BoundingBoxesOverlay';

interface Polygon {
  coords: number[][];
  class: 'live' | 'dead';
  confidence: number;
}

interface ImageDisplayProps {
  imageUrl: string;
  filename: string;
  polygons: Polygon[];
  scale: { scaleX: number; scaleY: number };
  isEditMode: boolean;
  editingPolygonIndex: number | null;
  visiblePolygons: boolean;
  onFullscreen: () => void;
  onPolygonClick: (index: number) => void;
  onPolygonHover: (index: number | null) => void;
  imageRef: React.RefObject<HTMLImageElement>;
}

export default function ImageDisplay({
  imageUrl,
  filename,
  polygons,
  scale,
  isEditMode,
  editingPolygonIndex,
  visiblePolygons,
  onFullscreen,
  onPolygonClick,
  onPolygonHover,
  imageRef,
}: ImageDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  return (
    <div className="lg:col-span-2">
      <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
        {imageUrl && (
          <div className="relative" ref={containerRef}>
            <button
              onClick={onFullscreen}
              className="absolute top-2 right-2 p-2 bg-white/90 dark:bg-zinc-800/90 backdrop-blur-sm rounded text-zinc-700 dark:text-zinc-300 hover:bg-white dark:hover:bg-zinc-700 z-10 shadow-lg"
              title="Zoom to fullscreen"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
              </svg>
            </button>

            {/* Image */}
            <img 
              ref={imageRef}
              src={imageUrl} 
              alt={filename}
              className="w-full h-auto rounded"
            />

            {visiblePolygons && (
              <BoundingBoxesOverlay
                polygons={polygons}
                scale={scale}
                isEditMode={isEditMode}
                editingPolygonIndex={editingPolygonIndex}
                onPolygonClick={onPolygonClick}
                onPolygonHover={onPolygonHover}
                imageRef={imageRef}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

