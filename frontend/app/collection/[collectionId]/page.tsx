'use client';

import { useRef, useEffect, useState, useMemo } from 'react';
import { useParams, useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useModels } from '@/hooks/useModels';
import { useCollectionData } from '@/hooks/useCollectionData';
import { useStorageData } from '@/hooks/useStorageData';
import { useImageUpload } from '@/hooks/useImageUpload';
import { useImageDelete } from '@/hooks/useImageDelete';
import { useStartRun } from '@/hooks/useStartRun';
import { useStopRun } from '@/hooks/useStopRun';
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
import { updateCollection } from '@/lib/api';

export default function RunResultsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const collectionId = parseInt(Array.isArray(params.collectionId) ? params.collectionId[0] : params.collectionId || '0', 10);

  const urlModelId = searchParams.get('modelId');
  const parsedModelId = urlModelId ? parseInt(urlModelId, 10) : NaN;
  const selectedModelId =
    Number.isInteger(parsedModelId) && parsedModelId > 0 ? parsedModelId : null;
  const sortBy = searchParams.get('sort') || '';
  
  const fileInputRef = useRef(null);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [savingName, setSavingName] = useState(false);
  const [runErrorDismissed, setRunErrorDismissed] = useState(false);

  // Custom hooks
  const { models } = useModels();
  const { collectionData, collection, images, latestRun, isRunning, threshold, setThreshold, loading, error, setError, setLoading, refetch } = useCollectionData(collectionId, selectedModelId);
  const { successMessage, setSuccessMessage, setRecentlyUploadedImageIds } = useStorageData();
  const { uploading, handleFileInputChange } = useImageUpload(collectionId, setError, setLoading, setRecentlyUploadedImageIds, setSuccessMessage);
  const { deletingImageId, handleDeleteImage } = useImageDelete(collectionId, setError, isRunning);
  
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
  const runFailureMsg = latestRun?.status === 'failed' ? (latestRun.error_msg || 'Run failed') : null;

  // Extract unique models that have been run on this collection
  const modelsUsed = useMemo(() => {
    if (!collectionData?.all_runs || !models) return [];
    
    const uniqueModelIds = new Set(
      collectionData.all_runs.map((run: { model_id: number }) => run.model_id)
    );
    
    return models
      .filter((model) => uniqueModelIds.has(model.model_id))
      .map((model) => model.name);
  }, [collectionData?.all_runs, models]);

  // URL is the source of truth for model selection.
  // If modelId is missing or invalid, default to the first available model and write it to URL.
  useEffect(() => {
    if (models.length === 0) return;
    const hasValidModel = selectedModelId !== null && models.some((m) => m.model_id === selectedModelId);
    if (hasValidModel) return;
    const firstModelId = models[0]?.model_id;
    if (!firstModelId) return;

    const params = new URLSearchParams(searchParams.toString());
    params.set('modelId', String(firstModelId));
    const query = params.toString();
    const hash = typeof window !== 'undefined' ? window.location.hash : '';
    router.replace(`${pathname}${query ? `?${query}` : ''}${hash}`);
  }, [selectedModelId, models, searchParams, router, pathname]);

  const handleSortChange = (newSort: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (newSort) {
      params.set('sort', newSort);
    } else {
      params.delete('sort');
    }
    const query = params.toString();
    const hash = typeof window !== 'undefined' ? window.location.hash : '';
    router.replace(`${pathname}${query ? `?${query}` : ''}${hash}`);
  };

  // Reset run error dismissal when run changes
  useEffect(() => {
    setRunErrorDismissed(false);
  }, [latestRun?.run_id]);

  // Scroll to hash anchor (for back from edit)
  useEffect(() => {
    if (!images || images.length === 0) return;
    const hash = typeof window !== 'undefined' ? window.location.hash : '';
    if (hash && hash.startsWith('#')) {
      const targetId = hash.slice(1);
      requestAnimationFrame(() => {
        const el = document.getElementById(targetId);
        if (el) {
          el.scrollIntoView({ block: 'start' });
        }
      });
    }
  }, [images]);

  const handleModelChange = (newModelId: number) => {
    const params = new URLSearchParams(searchParams.toString());
    if (Number.isInteger(newModelId) && newModelId > 0) {
      params.set('modelId', String(newModelId));
    } else {
      params.delete('modelId');
    }
    const query = params.toString();
    const hash = typeof window !== 'undefined' ? window.location.hash : '';
    router.replace(`${pathname}${query ? `?${query}` : ''}${hash}`);
  };

  // Collection name editing handlers
  const handleStartEdit = () => {
    setEditedName(collection.name || '');
    setIsEditingName(true);
  };

  const handleCancelEdit = () => {
    setIsEditingName(false);
    setEditedName('');
  };

  const handleSaveName = async () => {
    if (!editedName.trim()) {
      setError('Collection name cannot be empty');
      return;
    }

    setSavingName(true);
    try {
      await updateCollection(collectionId, { name: editedName.trim() });
      await refetch();
      setIsEditingName(false);
      setSuccessMessage('Collection name updated successfully');
    } catch (err) {
      setError((err as Error).message || 'Failed to update collection name');
    } finally {
      setSavingName(false);
    }
  };

  const handleDeleteAndRefresh = async (imageId: number) => {
    await handleDeleteImage(imageId);
    await refetch();
  };

  // Loading state
  if (loading && !collectionId) {
    return <LoadingState />;
  }

  // Error state (no collection data)
  if (error && !collectionData) {
    return <ErrorState error={error} />;
  }

  const displayError = error || (!runErrorDismissed ? runFailureMsg : null);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <PageHeader collectionName={collection.name} onModelSuccess={setSuccessMessage} onModelError={setError}>
          <AddImagesButton
            fileInputRef={fileInputRef}
            uploading={uploading}
            collectionId={collectionId}
            onFileChange={handleFileInputChange}
          />
        </PageHeader>

      <div className="max-w-6xl mx-auto p-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">
            Run Results
          </h1>
          <div className="mt-2 flex items-center gap-2">
            {isEditingName ? (
              <>
                <span className="text-zinc-600 dark:text-zinc-400">Collection:</span>
                <input
                  type="text"
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveName();
                    if (e.key === 'Escape') handleCancelEdit();
                  }}
                  className="px-2 py-1 text-sm border border-zinc-300 dark:border-zinc-600 rounded bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                  disabled={savingName}
                />
                <button
                  onClick={handleSaveName}
                  disabled={savingName}
                  className="px-2 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {savingName ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={handleCancelEdit}
                  disabled={savingName}
                  className="px-2 py-1 text-sm bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded hover:bg-zinc-300 dark:hover:bg-zinc-600"
                >
                  Cancel
                </button>
              </>
            ) : (
              <>
                {collection.name && (
                  <p className="text-zinc-600 dark:text-zinc-400">Collection: {collection.name}</p>
                )}
                <button
                  onClick={handleStartEdit}
                  className="p-1 text-zinc-600 dark:text-zinc-300 hover:text-blue-600 dark:hover:text-blue-400"
                  title="Edit collection name"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
              </>
            )}
          </div>
        </div>

        {modelsUsed.length > 0 && (
          <div className="mt-2 p-3 flex flex-wrap items-center gap-2 bg-zinc-50 dark:bg-zinc-900/50">
            <span className="text-sm text-zinc-600 dark:text-zinc-400">Models run:</span>
            {modelsUsed.map((modelName, idx) => (
              <span 
                key={idx}
                className="px-2 py-1 text-xs rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800"
              >
                {modelName}
              </span>
            ))}
          </div>
        )}

        <ErrorDisplay
          error={displayError}
          onDismiss={() => {
            if (error) {
              setError(null);
            } else {
              setRunErrorDismissed(true);
            }
          }}
        />

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
              !selectedModelId ||
              images.length === 0 ||
              !(collectionData?.can_start_run ?? false)
            }
            models={models}
            selectedModelId={selectedModelId}
            onModelChange={handleModelChange}
            imageCount={images.length}
            isRecalculating={isRecalculating}
            hasRecalculatedData={hasRecalculatedData}
            isRunning={isRunning}
          />
        </div>

        <ImageList
          images={images}
          onDeleteImage={handleDeleteAndRefresh}
          deletingImageId={deletingImageId}
          selectedModelId={selectedModelId}
          sortBy={sortBy}
          onSortChange={handleSortChange}
          isRunning={isRunning}
          latestRun={latestRun}
          recalculatedImages={recalculatedImages}
          collectionId={collectionId}
        />
      </div>
    </div>
  );
}
