'use client';

import { useEffect, useRef } from 'react';
import BoundingBoxesOverlay from './BoundingBoxesOverlay';

interface Polygon {
  coords: number[][];
  class: 'live' | 'dead';
  confidence: number;
}

interface FullscreenImageModalProps {
  isOpen: boolean;
  imageUrl: string;
  filename: string;
  polygons: Polygon[];
  scale: { scaleX: number; scaleY: number };
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
  scale,
  isEditMode,
  editingPolygonIndex,
  visiblePolygons,
  onClose,
  onPolygonClick,
  onPolygonHover,
}: FullscreenImageModalProps) {
  const fullscreenImageRef = useRef<HTMLImageElement>(null);
  const fullscreenContainerRef = useRef<HTMLDivElement>(null);

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
        className="relative max-w-full max-h-full"
        onClick={(e) => e.stopPropagation()}
        ref={fullscreenContainerRef}
      >
        {/* Image */}
        <img 
          ref={fullscreenImageRef}
          src={imageUrl} 
          alt={filename}
          className="max-w-full max-h-[95vh] object-contain rounded"
        />
        
        {visiblePolygons && (
          <BoundingBoxesOverlay
            polygons={polygons}
            scale={scale}
            isEditMode={isEditMode}
            editingPolygonIndex={editingPolygonIndex}
            onPolygonClick={onPolygonClick}
            onPolygonHover={onPolygonHover}
            imageRef={fullscreenImageRef}
          />
        )}
      </div>
    </div>
  );
}

