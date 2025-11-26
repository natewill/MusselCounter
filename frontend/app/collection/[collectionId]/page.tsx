'use client';

import { useRef } from 'react';
import { useParams } from 'next/navigation';
import { useModels } from '@/hooks/useModels';
import { useCollectionData } from '@/hooks/useCollectionData';
import { useStorageData } from '@/hooks/useStorageData';
import { useImageUpload } from '@/hooks/useImageUpload';
import { useImageDelete } from '@/hooks/useImageDelete';
import { useStartRun } from '@/hooks/useStartRun';
import { useStopRun } from '@/hooks/useStopRun';
import { useRunState } from '@/hooks/useRunState';
import PageHeader from '@/components/run/PageHeader';
import CollectionTotals from '@/components/run/CollectionTotals';
import RunStatus from '@/components/run/RunStatus';
import ThresholdControl from '@/components/run/ThresholdControl';
import ImageList from '@/components/run/ImageList';
import AddImagesButton from '@/components/run/AddImagesButton';
import ErrorDisplay from '@/components/run/ErrorDisplay';
import LoadingState from '@/components/run/LoadingState';
import ErrorState from '@/components/run/ErrorState';
import UploadProgress from '@/components/run/UploadProgress';
import SuccessMessage from '@/components/run/SuccessMessage';

export default function RunResultsPage() {
  const params = useParams();
  const collectionId = parseInt(Array.isArray(params.collectionId) ? params.collectionId[0] : params.collectionId || '0', 10);
  
  const fileInputRef = useRef(null);
  
  // Custom hooks
  const { models, selectedModelId, setSelectedModelId } = useModels();
  const { collectionId: resolvedCollectionId, collectionData, collection, images, latestRun, isRunning, threshold, setThreshold, loading, error, setError, setLoading } = useCollectionData(collectionId);
  const { successMessage, setSuccessMessage, recentlyUploadedImageIds, setRecentlyUploadedImageIds } = useStorageData();
  const { uploading, handleFileInputChange } = useImageUpload(collectionId, setError, setLoading, setRecentlyUploadedImageIds);
  const { deletingImageId, handleDeleteImage } = useImageDelete(collectionId, setError);

  // Use custom hook for run state management (flashing, green hue, etc.)
  const { flashingImageIds, greenHueImageIds } = useRunState(collectionData, recentlyUploadedImageIds, setRecentlyUploadedImageIds);
  
  // Handle starting new run
  const { handleStartNewRun } = useStartRun(collectionId, selectedModelId, threshold, loading, setLoading, setError);
  
  // Handle stopping run (refresh data on success)
  const { stopping, handleStopRun } = useStopRun(setError, () => setLoading(true));

  // Loading state
  if (loading && !collectionId) {
    return <LoadingState />;
  }

  // Error state (no collection data)
  if (error && !collectionData) {
    return <ErrorState error={error} />;
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="max-w-6xl mx-auto">
        <PageHeader collectionName={collection.name}>
          <AddImagesButton
            fileInputRef={fileInputRef}
            uploading={uploading}
            collectionId={collectionId}
            onFileChange={handleFileInputChange}
          />
        </PageHeader>

        <ErrorDisplay error={error} onDismiss={() => setError(null)} />

        <CollectionTotals collection={collection} imageCount={images.length} images={images} />

        {uploading && <UploadProgress />}

        <SuccessMessage message={successMessage} onDismiss={() => setSuccessMessage(null)} />

        {/* Two-column layout for Run Status and Run Settings */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <RunStatus 
            latestRun={latestRun} 
            isRunning={isRunning} 
            images={images} 
            onStopRun={handleStopRun}
            stopping={stopping}
          />
          
          <ThresholdControl
            threshold={threshold}
            onThresholdChange={setThreshold}
            onStartNewRun={handleStartNewRun}
            disabled={loading || uploading || isRunning}
            models={models}
            selectedModelId={selectedModelId}
            onModelChange={setSelectedModelId}
          />
        </div>

        <ImageList 
          images={images} 
          onDeleteImage={handleDeleteImage}
          deletingImageId={deletingImageId}
          selectedModelId={selectedModelId}
          flashingImageIds={flashingImageIds}
          greenHueImageIds={greenHueImageIds}
          isRunning={isRunning}
          currentThreshold={threshold}
          latestRun={latestRun}
        />
      </div>
    </div>
  );
}

