'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { getImageDetails } from '@/lib/api';
import Link from 'next/link';
import { updatePolygonClassification } from '@/lib/api';

export default function ImageDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const imageId = parseInt(Array.isArray(params.imageId) ? params.imageId[0] : params.imageId || '0', 10);
  const runId = parseInt(searchParams.get('runId') || '0', 10);
  
  const [imageData, setImageData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [imageScale, setImageScale] = useState({ scaleX: 1, scaleY: 1 });
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // editing related states
  const [editingPolygonIndex, setEditingPolygonIndex] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedPolygonIndex, setSelectedPolygonIndex] = useState<number | null>(null);

  const [visiblePolygons, setVisiblePolygons] = useState<boolean>(true);

  // fullscreen related states
  const [isFullscreen, setIsFullscreen] = useState(false);
  const fullscreenImageRef = useRef<HTMLImageElement>(null);
  const fullscreenContainerRef = useRef<HTMLDivElement>(null);
  const [fullscreenScale, setFullscreenScale] = useState({ scaleX: 1, scaleY: 1 });

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
        console.log(data);
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

  // Calculate scale when image loads
  useEffect(() => {
    const updateScale = () => {
      if (imageRef.current && imageData) {
        const displayedWidth = imageRef.current.offsetWidth;
        const displayedHeight = imageRef.current.offsetHeight;
        const originalWidth = imageData.width || displayedWidth;
        const originalHeight = imageData.height || displayedHeight;
        
        setImageScale({
          scaleX: displayedWidth / originalWidth,
          scaleY: displayedHeight / originalHeight,
        });
      }
    };

    // Update scale when image loads or window resizes (i.e. when image changes size)
    if (imageRef.current) {
      imageRef.current.addEventListener('load', updateScale);
      window.addEventListener('resize', updateScale);
      updateScale();
    }

    return () => {
      if (imageRef.current) {
        imageRef.current.removeEventListener('load', updateScale);
      }
      window.removeEventListener('resize', updateScale);
    };
  }, [imageData]);

  // Calculate scale for fullscreen image
  useEffect(() => {
    if (!isFullscreen || !fullscreenImageRef.current || !imageData) return;
    
    const updateFullscreenScale = () => {
      if (fullscreenImageRef.current) {
        const displayedWidth = fullscreenImageRef.current.offsetWidth;
        const displayedHeight = fullscreenImageRef.current.offsetHeight;
        const originalWidth = imageData.width || displayedWidth;
        const originalHeight = imageData.height || displayedHeight;
        
        setFullscreenScale({
          scaleX: displayedWidth / originalWidth,
          scaleY: displayedHeight / originalHeight,
        });
      }
    };

    if (fullscreenImageRef.current) {
      fullscreenImageRef.current.addEventListener('load', updateFullscreenScale);
      window.addEventListener('resize', updateFullscreenScale);
      updateFullscreenScale();
    }

    return () => {
      if (fullscreenImageRef.current) {
        fullscreenImageRef.current.removeEventListener('load', updateFullscreenScale);
      }
      window.removeEventListener('resize', updateFullscreenScale);
    };
  }, [isFullscreen, imageData]);


  // Add ESC key handler to close fullscreen
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isFullscreen]);

  
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center text-zinc-600 dark:text-zinc-400">Loading image details...</div>
        </div>
      </div>
    );
  }

  if (error || !imageData) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <div className="max-w-6xl mx-auto">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-800 dark:text-red-200">{error || 'Image not found'}</p>
            <Link
              href={`/collection/${imageData?.collection_id || ''}`}
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

  // handle classification change for polygon/mussel
  const handleClassificationChange = async (polygonIndex: number, newClass: 'live' | 'dead') => {
    if (saving) return;
    
    setSaving(true);
    try {
      const result = await updatePolygonClassification(imageId, runId, polygonIndex, newClass);
      
      // Refresh image data to show updated counts
      const updatedData = await getImageDetails(imageId, runId);
      setImageData(updatedData);
      
      // Close modal after successful update
      setSelectedPolygonIndex(null);
      
      console.log('Classification updated:', result);
    } catch (err) {
      console.error('Failed to update classification:', err);
      setError((err as Error).message || 'Failed to update classification');
    } finally {
      setSaving(false);
    }
  };

  // Get selected polygon data for modal
  const selectedPolygon = selectedPolygonIndex !== null && imageData.polygons 
    ? imageData.polygons[selectedPolygonIndex] 
    : null;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header with back button */}
        <div className="mb-6">
          <Link
            href={`/collection/${imageData.collection_id}`}
            className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-2 mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to collection
          </Link>
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{imageData.filename}</h1>
            <button
              onClick={() => setIsEditMode(!isEditMode)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                isEditMode
                  ? 'bg-green-600 dark:bg-green-500 text-white hover:bg-green-700 dark:hover:bg-green-600'
                  : 'bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-300 dark:hover:bg-zinc-600'
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              {isEditMode ? 'Edit Image' : 'Edit Image'}
            </button>
            <button
              onClick={() => setVisiblePolygons(!visiblePolygons)}
              className="px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 text-zinc-900 dark:text-zinc-100"
              title={visiblePolygons ? 'Hide Boxes' : 'Show Boxes'}
            >
              {visiblePolygons ? (
                // Open eye (visible)
                <>
                  <text>Bounding Boxes Visible</text>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </>
              ) : (
                // Closed/slashed eye (hidden)
                <>
                  <text>Bounding Boxes Hidden</text>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Image with bounding boxes */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
              {imageUrl && (
                <div className="relative" ref={containerRef}>
                  <button
                    onClick={() => setIsFullscreen(true)}
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
                    alt={imageData.filename}
                    className="w-full h-auto rounded"
                  />

                  {visiblePolygons && (
                    <>
                    {/* Bounding Boxes */}
                    {imageData.polygons && imageData.polygons.length > 0 && (
                      <svg
                        className="absolute top-0 left-0 w-full h-full pointer-events-none rounded"
                        style={{
                          width: imageRef.current?.offsetWidth || '100%',
                          height: imageRef.current?.offsetHeight || 'auto',
                        }}
                      >
                        {imageData.polygons.map((polygon: any, index: number) => {
                          // Scale coordinates
                          const scaledCoords = polygon.coords.map((coord: number[]) => [
                            coord[0] * imageScale.scaleX,
                            coord[1] * imageScale.scaleY,
                          ]);

                          const pathData = scaledCoords
                            .map((coord: number[], i: number) => 
                              `${i === 0 ? 'M' : 'L'} ${coord[0]} ${coord[1]}`
                            )
                            .join(' ') + ' Z';

                          // Color based on class
                          const strokeColor = polygon.class === 'live' 
                            ? '#22c55e' // green-500
                            : '#ef4444'; // red-500
                          
                          const fillColor = polygon.class === 'live'
                            ? 'rgba(34, 197, 94, 0.1)' 
                            : 'rgba(239, 68, 68, 0.1)';

                          return (
                            <g 
                              key={index}
                              style={{ cursor: isEditMode ? 'pointer' : 'default' }}
                              className={isEditMode ? "pointer-events-auto" : "pointer-events-none"}
                            >
                              {/* bounding box */}
                              <path
                                d={pathData}
                                fill={editingPolygonIndex === index ? fillColor.replace('0.1', '0.3') : fillColor}
                                stroke={strokeColor}
                                strokeWidth={editingPolygonIndex === index ? "3" : "2"}
                                className={`transition-opacity ${isEditMode ? "hover:opacity-80 pointer-events-auto" : "pointer-events-none"}`}
                                onMouseEnter={() => isEditMode && setEditingPolygonIndex(index)}
                                onMouseLeave={() => setEditingPolygonIndex(null)}
                                onClick={() => {
                                  if (isEditMode) {
                                    setSelectedPolygonIndex(index);
                                  }
                                }}
                              />

                              {/* label w/ confidence */}
                              {scaledCoords[0] && (() => {
                                const labelText = `${polygon.class} ${(polygon.confidence * 100).toFixed(0)}%`;
                                const labelX = scaledCoords[0][0];
                                const labelY = scaledCoords[0][1] - 5;

                                const textWidth = labelText.length * 6;
                                const textHeight = 14;
                                const padding = 4;
                                const rectWidth = textWidth + padding * 2;
                                const rectHeight = textHeight + padding * 2;
                                
                                return (
                                  <g
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      if (isEditMode) {
                                        setSelectedPolygonIndex(index);
                                      }
                                    }}
                                    style={{ cursor: isEditMode ? 'pointer' : 'default' }}
                                    className={`transitionopacity: ${isEditMode ? "hover:opacity-80 pointer-events-auto" : "pointer-events-none"}`}
                                  >
                                    {/* label box */}
                                    <rect
                                      x={labelX - padding}
                                      y={labelY - textHeight - padding}
                                      width={rectWidth + (polygon.class === 'dead' ? 7 : 0)}
                                      height={rectHeight}
                                      fill="white"
                                      stroke="black"
                                      strokeWidth="1.5"
                                      rx="2"
                                      className={isEditMode ? "hover:opacity-80 transition-opacity" : ""}
                                    />
                                    {/* text */}
                                    <text
                                      x={labelX}
                                      y={labelY - padding / 2}
                                      fill="black"
                                      fontSize="12"
                                      fontWeight="bold"
                                    >
                                      {labelText}
                                    </text>
                                  </g>
                                );
                              })()}
                            </g>
                          );
                        })}
                      </svg>
                    )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* stats */}
          <div className="space-y-6">
            {/* Counts */}
            <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
              <h2 className="text-xl font-semibold mb-4 text-zinc-900 dark:text-zinc-100">Statistics</h2>
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-zinc-600 dark:text-zinc-400">Live Mussels</div>
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {imageData.live_mussel_count}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-zinc-600 dark:text-zinc-400">Dead Mussels</div>
                  <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {imageData.dead_mussel_count}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-zinc-600 dark:text-zinc-400">Total</div>
                  <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                    {imageData.total_mussel_count}
                  </div>
                </div>
                {imageData.live_percentage !== null && (
                  <div>
                    <div className="text-sm text-zinc-600 dark:text-zinc-400">Live Percentage</div>
                    <div className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                      {imageData.live_percentage}%
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Model Info */}
            <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
              <h2 className="text-xl font-semibold mb-4 text-zinc-900 dark:text-zinc-100">Model Information</h2>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-zinc-600 dark:text-zinc-400">Model: </span>
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">
                    {imageData.model_name} ({imageData.model_type})
                  </span>
                </div>
                <div>
                  <span className="text-zinc-600 dark:text-zinc-400">Threshold: </span>
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">{imageData.threshold}</span>
                </div>
                <div>
                  <span className="text-zinc-600 dark:text-zinc-400">Processed: </span>
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">
                    {new Date(imageData.processed_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Image Details */}
            <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
              <h2 className="text-xl font-semibold mb-4 text-zinc-900 dark:text-zinc-100">Image Details</h2>
              <div className="space-y-2 text-sm">
                {imageData.width && imageData.height && (
                  <div>
                    <span className="text-zinc-600 dark:text-zinc-400">Dimensions: </span>
                    <span className="font-medium text-zinc-900 dark:text-zinc-100">
                      {imageData.width} × {imageData.height}
                    </span>
                  </div>
                )}
                <div>
                  <span className="text-zinc-600 dark:text-zinc-400">File Hash: </span>
                  <span className="font-mono text-xs text-zinc-500 dark:text-zinc-400">
                    {imageData.file_hash}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-600 dark:text-zinc-400">Uploaded: </span>
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">
                    {new Date(imageData.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>


        {/* Modal for fullscreen image */}
        {isFullscreen && imageUrl && (
          <div 
            className="fixed inset-0 bg-black z-50 flex items-center justify-center p-4"
            onClick={() => setIsFullscreen(false)}
          >
            {/* Close button */}
            <button
              onClick={() => setIsFullscreen(false)}
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
                alt={imageData.filename}
                className="max-w-full max-h-[95vh] object-contain rounded"
              />
              
              {visiblePolygons && (
              <>
                {/* Bounding boxes */}
                {imageData.polygons && imageData.polygons.length > 0 && (
                  <svg
                    className="absolute top-0 left-0 pointer-events-none rounded"
                    style={{
                      width: fullscreenImageRef.current?.offsetWidth || '100%',
                      height: fullscreenImageRef.current?.offsetHeight || 'auto',
                    }}
                  >
                    {imageData.polygons.map((polygon: any, index: number) => {
                      
                      // scale box coordinates again
                      const scaledCoords = polygon.coords.map((coord: number[]) => [
                        coord[0] * fullscreenScale.scaleX,
                        coord[1] * fullscreenScale.scaleY,
                      ]);

                      const pathData = scaledCoords
                        .map((coord: number[], i: number) => 
                          `${i === 0 ? 'M' : 'L'} ${coord[0]} ${coord[1]}`
                        )
                        .join(' ') + ' Z';

                      const strokeColor = polygon.class === 'live' 
                        ? '#22c55e'
                        : '#ef4444';
                      
                      const fillColor = polygon.class === 'live'
                        ? 'rgba(34, 197, 94, 0.1)'
                        : 'rgba(239, 68, 68, 0.1)';

                      return (
                        <g 
                          key={index}
                          style={{ cursor: isEditMode ? 'pointer' : 'default' }}
                          className={isEditMode ? "pointer-events-auto" : "pointer-events-none"}
                          onClick={() => {
                            if (isEditMode) {
                              setSelectedPolygonIndex(index);
                            }
                          }}
                        >
                          <path
                            d={pathData}
                            fill={fillColor}
                            stroke={strokeColor}
                            strokeWidth="2"
                            className={`transition-opacity ${isEditMode ? "hover:opacity-80 pointer-events-auto" : "pointer-events-none"}`}
                            onMouseEnter={() => isEditMode && setEditingPolygonIndex(index)}
                            onMouseLeave={() => setEditingPolygonIndex(null)}
                          />

                          {/* Label */}
                          {scaledCoords[0] && (() => {
                            const labelText = `${polygon.class} ${(polygon.confidence * 100).toFixed(0)}%`;
                            const labelX = scaledCoords[0][0];
                            const labelY = scaledCoords[0][1] - 5;

                            const textWidth = labelText.length * 6;
                            const textHeight = 14;
                            const padding = 4;
                            const rectWidth = textWidth + padding * 2;
                            const rectHeight = textHeight + padding * 2;
                            
                            return (
                              <g
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (isEditMode) {
                                    setSelectedPolygonIndex(index);
                                  }
                                }}
                                style={{ cursor: isEditMode ? 'pointer' : 'default' }}
                                className={isEditMode ? "pointer-events-auto" : "pointer-events-none"}
                              >
                                <rect
                                  x={labelX - padding}
                                  y={labelY - textHeight - padding}
                                  width={rectWidth}
                                  height={rectHeight}
                                  fill="white"
                                  stroke="black"
                                  strokeWidth="1.5"
                                  rx="2"
                                  className={isEditMode ? "hover:opacity-80 transition-opacity" : ""}
                                />
                                <text
                                  x={labelX}
                                  y={labelY - padding / 2}
                                  fill="black"
                                  fontSize="12"
                                  fontWeight="bold"
                                >
                                  {labelText}
                                </text>
                              </g>
                            );
                          })()}
                        </g>
                      );
                    })}
                  </svg>
                )}
                </>
              )}
            </div>
          </div>
        )}


        {/* Modal for editing polygon */}
        {selectedPolygonIndex !== null && selectedPolygon && (
          <div 
            className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedPolygonIndex(null)}
          >
            <div 
              className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 max-w-md w-full shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                  Edit Mussel #{selectedPolygonIndex + 1}
                </h2>
                <button
                  onClick={() => setSelectedPolygonIndex(null)}
                  className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-1">Current Classification</div>
                  <div className={`text-lg font-semibold ${
                    selectedPolygon.class === 'live' 
                      ? 'text-green-600 dark:text-green-400' 
                      : 'text-red-600 dark:text-red-400'
                  }`}>
                    {selectedPolygon.class.charAt(0).toUpperCase() + selectedPolygon.class.slice(1)}
                  </div>
                </div>
                
                {selectedPolygon.manually_edited && (
                  <div>
                    <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-1">Manually Edited</div>
                    <div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                      Yes
                    </div>
                  </div>
                )}
                {!selectedPolygon.manually_edited && (
                  <div>
                    <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-1">Manually Edited</div>
                    <div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                      No
                    </div>
                  </div>
                )}
                
                <div>
                  <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-1">Confidence</div>
                  <div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                    {(selectedPolygon.confidence * 100).toFixed(1)}% {selectedPolygon.original_class ? selectedPolygon.original_class.charAt(0).toUpperCase() + selectedPolygon.original_class.slice(1) : selectedPolygon.class.charAt(0).toUpperCase() + selectedPolygon.class.slice(1)}
                  </div>
                </div>

                <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800">
                  <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">Change Classification</div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleClassificationChange(selectedPolygonIndex, 'live')}
                      disabled={saving || selectedPolygon.class === 'live'}
                      className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                        selectedPolygon.class === 'live'
                          ? 'bg-green-600 dark:bg-green-500 text-white cursor-not-allowed'
                          : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50'
                      } disabled:opacity-50`}
                    >
                      Live
                    </button>
                    <button
                      onClick={() => handleClassificationChange(selectedPolygonIndex, 'dead')}
                      disabled={saving || selectedPolygon.class === 'dead'}
                      className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                        selectedPolygon.class === 'dead'
                          ? 'bg-red-600 dark:bg-red-500 text-white cursor-not-allowed'
                          : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50'
                      } disabled:opacity-50`}
                    >
                      Dead
                    </button>
                  </div>
                </div>

                {saving && (
                  <div className="text-sm text-zinc-600 dark:text-zinc-400 text-center">
                    Saving...
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}