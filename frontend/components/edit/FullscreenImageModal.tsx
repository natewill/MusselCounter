'use client';

import { useEffect, useState } from 'react';
import BoundingBoxesOverlay from './BoundingBoxesOverlay';

interface Polygon {
  bbox: number[];
  class: 'live' | 'dead';
  confidence: number;
}

interface FullscreenImageModalProps {
  isOpen: boolean;
  imageUrl: string;
  filename: string;
  polygons: Polygon[];
  isEditMode: boolean;
  editingPolygonIndex: number | null;
  visiblePolygons: boolean;
  onClose: () => void;
  onPolygonClick: (index: number) => void;
  onPolygonHover: (index: number | null) => void;
}

export default function FullscreenImageModal({
  isOpen,
  imageUrl,
  filename,
  polygons,
  isEditMode,
  editingPolygonIndex,
  visiblePolygons,
  onClose,
  onPolygonClick,
  onPolygonHover,
}: FullscreenImageModalProps) {
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });

  // Add ESC key handler to close fullscreen
  useEffect(() => {
    if (!isOpen) return;
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    setNaturalSize({ width: 0, height: 0 });
  }, [isOpen, imageUrl]);

  if (!isOpen || !imageUrl) return null;

  return (
    <div 
      className="fixed inset-0 bg-black z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-3 bg-white/90 dark:bg-zinc-800/90 backdrop-blur-sm rounded-full text-zinc-700 dark:text-zinc-300 hover:bg-white dark:hover:bg-zinc-700 z-20 shadow-lg"
        title="Close fullscreen (ESC)"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Image container */}
      <div
        className="relative max-w-[95vw] max-h-[95vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative inline-block">
          <img
            src={imageUrl}
            alt={filename}
            className="block max-w-none max-h-none rounded"
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
    </div>
  );
}
