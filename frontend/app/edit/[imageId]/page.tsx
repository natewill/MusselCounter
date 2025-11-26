'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { getImageDetails, updatePolygonClassification } from '@/lib/api';
import Link from 'next/link';
import ImageHeader from '@/components/edit/ImageHeader';
import ImageDisplay from '@/components/edit/ImageDisplay';
import ImageStatsPanel from '@/components/edit/ImageStatsPanel';
import FullscreenImageModal from '@/components/edit/FullscreenImageModal';
import EditPolygonModal from '@/components/edit/EditPolygonModal';
import { useImageScale } from '@/hooks/useImageScale';

interface Polygon {
  coords: number[][];
  class: 'live' | 'dead';
  confidence: number;
  original_class?: string;
  manually_edited: boolean;
}

interface ImageData {
  image_id: number;
  collection_id: number;
  filename: string;
  stored_path: string;
  file_hash: string;
  width?: number;
  height?: number;
  live_mussel_count: number;
  dead_mussel_count: number;
  total_mussel_count: number;
  live_percentage: number | null;
  model_name: string;
  model_type: string;
  threshold: number;
  processed_at: string;
  created_at: string;
  polygons: Polygon[];
}

export default function ImageDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const imageId = parseInt(Array.isArray(params.imageId) ? params.imageId[0] : params.imageId || '0', 10);
  const runId = parseInt(searchParams.get('runId') || '0', 10);
  
  const [imageData, setImageData] = useState<ImageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const imageRef = useRef<HTMLImageElement>(null);
  const fullscreenImageRef = useRef<HTMLImageElement>(null);

  // Editing related states
  const [editingPolygonIndex, setEditingPolygonIndex] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedPolygonIndex, setSelectedPolygonIndex] = useState<number | null>(null);
  const [visiblePolygons, setVisiblePolygons] = useState<boolean>(true);

  // Fullscreen related states
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Calculate scale for main image
  const imageScale = useImageScale({ imageRef, imageData });
  
  // Calculate scale for fullscreen image
  const fullscreenScale = useImageScale({ 
    imageRef: fullscreenImageRef, 
    imageData, 
    enabled: isFullscreen 
  });

  // Fetch image data
  useEffect(() => {
    if (!imageId || !runId) {
      setError('Image ID and Run ID are required');
      setLoading(false);
      return;
    }

    const fetchImageData = async () => {
      try {
        setLoading(true);
        const data = await getImageDetails(imageId, runId);
        setImageData(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load image data:', err);
        setError((err as Error).message || 'Failed to load image details');
      } finally {
        setLoading(false);
      }
    };

    fetchImageData();
  }, [imageId, runId]);

  // Handle classification change for polygon/mussel
  const handleClassificationChange = async (polygonIndex: number, newClass: 'live' | 'dead') => {
    if (saving) return;
    
    setSaving(true);
    try {
      await updatePolygonClassification(imageId, runId, polygonIndex, newClass);
      
      // Refresh image data to show updated counts
      const updatedData = await getImageDetails(imageId, runId);
      setImageData(updatedData);
      
      // Close modal after successful update
      setSelectedPolygonIndex(null);
    } catch (err) {
      console.error('Failed to update classification:', err);
      setError((err as Error).message || 'Failed to update classification');
    } finally {
      setSaving(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center text-zinc-600 dark:text-zinc-400">Loading image details...</div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !imageData) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <div className="max-w-6xl mx-auto">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-800 dark:text-red-200">{error || 'Image not found'}</p>
            <Link
              href={`/collection/${imageData?.collection_id || ''}?runId=${runId || ''}`}
              className="text-blue-600 dark:text-blue-400 hover:underline mt-2 inline-block"
            >
              ← Back to collection
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const imageUrl = imageData.stored_path 
    ? `http://127.0.0.1:8000/uploads/${imageData.stored_path.split('/').pop()}`
    : null;

  // Get selected polygon data for modal
  const selectedPolygon = selectedPolygonIndex !== null && imageData.polygons 
    ? imageData.polygons[selectedPolygonIndex] 
    : null;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="max-w-6xl mx-auto">
        <ImageHeader
          filename={imageData.filename}
          collectionId={imageData.collection_id}
          runId={runId}
          isEditMode={isEditMode}
          onToggleEditMode={() => setIsEditMode(!isEditMode)}
          visiblePolygons={visiblePolygons}
          onToggleVisiblePolygons={() => setVisiblePolygons(!visiblePolygons)}
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <ImageDisplay
            imageUrl={imageUrl || ''}
            filename={imageData.filename}
            polygons={imageData.polygons || []}
            scale={imageScale}
            isEditMode={isEditMode}
            editingPolygonIndex={editingPolygonIndex}
            visiblePolygons={visiblePolygons}
            onFullscreen={() => setIsFullscreen(true)}
            onPolygonClick={(index) => setSelectedPolygonIndex(index)}
            onPolygonHover={(index) => setEditingPolygonIndex(index)}
            imageRef={imageRef}
          />

          <ImageStatsPanel imageData={imageData} />
        </div>

        <FullscreenImageModal
          isOpen={isFullscreen}
          imageUrl={imageUrl || ''}
          filename={imageData.filename}
          polygons={imageData.polygons || []}
          scale={fullscreenScale}
          isEditMode={isEditMode}
          editingPolygonIndex={editingPolygonIndex}
          visiblePolygons={visiblePolygons}
          onClose={() => setIsFullscreen(false)}
          onPolygonClick={(index) => {
            setSelectedPolygonIndex(index);
            setIsFullscreen(false);
          }}
          onPolygonHover={(index) => setEditingPolygonIndex(index)}
        />

        <EditPolygonModal
          isOpen={selectedPolygonIndex !== null}
          polygon={selectedPolygon}
          polygonIndex={selectedPolygonIndex}
          saving={saving}
          onClose={() => setSelectedPolygonIndex(null)}
          onClassificationChange={(newClass) => {
            if (selectedPolygonIndex !== null) {
              handleClassificationChange(selectedPolygonIndex, newClass);
            }
          }}
        />
      </div>
    </div>
  );
}
