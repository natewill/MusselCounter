'use client';

import { useRef, useEffect } from 'react';
import { useParams, useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useModels } from '@/hooks/useModels';
import { useCollectionData } from '@/hooks/useCollectionData';
import { useStorageData } from '@/hooks/useStorageData';
import { useImageUpload } from '@/hooks/useImageUpload';
import { useImageDelete } from '@/hooks/useImageDelete';
import { useStartRun } from '@/hooks/useStartRun';
import { useStopRun } from '@/hooks/useStopRun';
import { useRunState } from '@/hooks/useRunState';
import { useThresholdRecalculation } from '@/hooks/useThresholdRecalculation';
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
import { shouldEnableStartRunButton } from '@/utils/run/runUtils';

export default function RunResultsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const collectionId = parseInt(Array.isArray(params.collectionId) ? params.collectionId[0] : params.collectionId || '0', 10);

  // Parse initial model from URL for first render
  const urlModelId = searchParams.get('modelId');
  const initialModelId = urlModelId ? parseInt(urlModelId, 10) : null;
  
  const fileInputRef = useRef(null);
  
  // Custom hooks
  const { models, selectedModelId, setSelectedModelId } = useModels(initialModelId);
  const { collectionId: resolvedCollectionId, collectionData, collection, images, latestRun, isRunning, serverTime, threshold, setThreshold, loading, error, setError, setLoading } = useCollectionData(collectionId, selectedModelId);
  const { successMessage, setSuccessMessage, recentlyUploadedImageIds, setRecentlyUploadedImageIds } = useStorageData();
  const { uploading, handleFileInputChange } = useImageUpload(collectionId, setError, setLoading, setRecentlyUploadedImageIds, setSuccessMessage);
  const { deletingImageId, handleDeleteImage } = useImageDelete(collectionId, setError, isRunning);

  // Use custom hook for run state management (flashing, green hue, etc.)
  const { flashingImageIds, greenHueImageIds } = useRunState(collectionData, recentlyUploadedImageIds, setRecentlyUploadedImageIds);
  
  // Handle starting new run
  const { handleStartNewRun } = useStartRun(collectionId, selectedModelId, threshold, loading, setLoading, setError);

  // Handle stopping run (refresh data on success)
  const { stopping, handleStopRun } = useStopRun(setError, () => setLoading(true));

  // Threshold recalculation without re-running model
  const {
    recalculatedImages,
    recalculatedTotals,
    isRecalculating,
    hasRecalculatedData
  } = useThresholdRecalculation(
    collectionId,
    threshold,
    selectedModelId,
    latestRun?.threshold,
    latestRun?.model_id,
    isRunning
  );

  const lastUrlModelIdRef = useRef<string | null>(null);
  const initializedFromUrlRef = useRef(false);

  // One-time sync from ?modelId= in URL to picker
  useEffect(() => {
    if (initializedFromUrlRef.current) return;

    const urlModelId = searchParams.get('modelId');
    initializedFromUrlRef.current = true;

    console.log('[ModelSync] Initial load - urlModelId:', urlModelId);

    if (urlModelId) {
      lastUrlModelIdRef.current = urlModelId;
      const parsed = parseInt(urlModelId, 10);
      if (!Number.isNaN(parsed)) {
        console.log('[ModelSync] Applying model from URL:', parsed);
        setSelectedModelId(parsed);
      } else {
        console.log('[ModelSync] urlModelId was not a number, ignoring.');
      }
    } else {
      console.log('[ModelSync] No modelId in URL on load.');
    }
  }, [searchParams, setSelectedModelId]);

  // Keep URL in sync when picker changes
  useEffect(() => {
    if (selectedModelId === null) return;

    const currentUrlModelId = searchParams.get('modelId');
    const currentParsed = currentUrlModelId ? parseInt(currentUrlModelId, 10) : null;

    if (currentParsed === selectedModelId) {
      console.log('[ModelSync] URL already matches selected model:', selectedModelId);
      return;
    }

    const params = new URLSearchParams(searchParams.toString());
    params.set('modelId', selectedModelId.toString());
    console.log('[ModelSync] Updating URL modelId', {
      from: currentParsed,
      to: selectedModelId,
      pathname,
      params: params.toString(),
    });
    router.replace(`${pathname}?${params.toString()}`);
  }, [selectedModelId, searchParams, router, pathname]);

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

        <CollectionTotals
          collection={collection}
          imageCount={images.length}
          images={images}
          recalculatedTotals={recalculatedTotals}
        />

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
            disabled={
              loading ||
              uploading ||
              isRunning ||
              images.length === 0 ||
              !shouldEnableStartRunButton(images, selectedModelId, latestRun, recentlyUploadedImageIds)
            }
            models={models}
            selectedModelId={selectedModelId}
            onModelChange={setSelectedModelId}
            imageCount={images.length}
            isRecalculating={isRecalculating}
            hasRecalculatedData={hasRecalculatedData}
            isRunning={isRunning}
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
          recalculatedImages={recalculatedImages}
        />
      </div>
    </div>
  );
}
