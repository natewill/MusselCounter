'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createBatch, uploadImagesToBatch, startRun, getModels } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeBatchId, setActiveBatchId] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  // Load activeBatchId from localStorage on mount
  useEffect(() => {
    const storedBatchId = localStorage.getItem('quickProcessBatchId');
    if (storedBatchId) {
      setActiveBatchId(parseInt(storedBatchId, 10));
    }
    
    // Load models on mount (with fallback)
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const modelsList = await getModels();
      console.log('Models loaded:', modelsList);
      if (modelsList && modelsList.length > 0) {
        setModels(modelsList);
        setSelectedModelId(modelsList[0].model_id);
        console.log('Models loaded:', modelsList);
      } else {
        // Fallback to model_id: 1 if no models found
        setModels([]);
        setSelectedModelId(1);
        console.log('No models found, using default model_id: 1');
      }
    } catch (err) {
      console.warn('Failed to load models (backend may not be running):', err);
      // Fallback to model_id: 1 - component will still work
      setModels([]);
      setSelectedModelId(1);
    }
  };

  const createQuickProcessBatch = async () => {
    const batchName = `Quick Process - ${new Date().toLocaleString()}`;
    const batchResponse = await createBatch(batchName, null);
    const batchId = batchResponse.batch_id;
    setActiveBatchId(batchId);
    localStorage.setItem('quickProcessBatchId', batchId.toString());
    console.log('Quick Process batch created:', batchId);
    return batchId;
  };

  const handleFileSelect = async (files) => {
    if (!files || files.length === 0) return;

    // Validate image files
    const imageFiles = Array.from(files).filter((file) => {
      if (!(file instanceof File)) return false;
      const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff'];
      return validTypes.includes(file.type);
    });

    if (imageFiles.length === 0) {
      setError('Please select valid image files');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let batchId = activeBatchId;

      // Create batch if needed
      if (!batchId) {
        try {
          batchId = await createQuickProcessBatch();
        } catch (err) {
          console.error('Failed to create batch:', err);
          throw new Error('Failed to create batch. Is the backend running?');
        }
      }

      // Upload files
      try {
        await uploadImagesToBatch(batchId, imageFiles);
        console.log('Files uploaded successfully');
      } catch (err) {
        const errorMsg = err.message || '';
        // If batch not found (404), clear stale batch_id - user can retry
        if (errorMsg.includes('404') || errorMsg.includes('Batch not found') || errorMsg.includes('HTTP 404')) {
          console.warn('Batch not found, clearing stale batch_id');
          setActiveBatchId(null);
          localStorage.removeItem('quickProcessBatchId');
          throw new Error('Batch not found. Please try uploading again.');
        } else {
          throw new Error('Failed to upload files. ' + errorMsg);
        }
      }

      // Start run (use selectedModelId or fallback to 1)
      const modelId = selectedModelId || 1;
      try {
        // threshold is optional, will use backend default (0.5)
        const runResponse = await startRun(batchId, modelId, undefined);
        console.log('Run started:', runResponse);

        // Navigate to run page
        if (runResponse.run_id) {
          router.push(`/run/${runResponse.run_id}`);
        } else {
          // If run_id not in response yet (placeholder), navigate with batch_id
          router.push(`/batches/${batchId}`);
        }
      } catch (err) {
        // If batch not found (404), clear stale batch_id and show error
        const errorMsg = err.message || '';
        if (errorMsg.includes('404') || errorMsg.includes('Batch not found') || errorMsg.includes('HTTP 404')) {
          console.warn('Batch not found when starting run, clearing stale batch_id');
          setActiveBatchId(null);
          localStorage.removeItem('quickProcessBatchId');
          throw new Error('Batch not found. Please try uploading again.');
        } else {
          console.error('Failed to start run:', err);
          throw new Error('Failed to start inference run. ' + errorMsg);
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to process images. Make sure the backend is running.');
      setLoading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    handleFileSelect(files);
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    handleFileSelect(files);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFolderClick = () => {
    folderInputRef.current?.click();
  };

  const handleFolderInputChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files);
    }
  };

  const handleCreateBatch = () => {
    // Navigate to batches page (or show form - keeping it simple for now)
    try {
      router.push('/batches');
    } catch (err) {
      console.warn('Navigation failed (page may not exist yet):', err);
      setError('Batches page not available yet');
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black relative">
      {/* Top Bar - Model Picker and Create Batch Button */}
      <div className="absolute top-4 left-4 right-4 flex justify-between items-center gap-4">
        {/* Model Picker */}
        <div className="flex items-center gap-2">
          <label htmlFor="model-select" className="text-sm text-zinc-700 dark:text-zinc-300">
            Model:
          </label>
          <select
            id="model-select"
            value={selectedModelId || ''}
            onChange={(e) => setSelectedModelId(parseInt(e.target.value, 10))}
            disabled={loading || models.length === 0}
            className="px-3 py-2 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-300 dark:border-zinc-600 rounded hover:bg-zinc-50 dark:hover:bg-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {models.length === 0 ? (
              <option value="">No models available</option>
            ) : (
              models.map((model) => (
                <option key={model.model_id} value={model.model_id}>
                  {model.name} ({model.type})
                </option>
              ))
            )}
          </select>
        </div>

        {/* Create Batch Button */}
        <button
          onClick={handleCreateBatch}
          className="px-4 py-2 bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-300 dark:hover:bg-zinc-700"
          disabled={loading}
        >
          Create Batch
        </button>
      </div>

      {/* Main Upload Area */}
      <div className="flex items-center justify-center min-h-screen p-8">
        <div className="w-full max-w-4xl">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleUploadClick}
            className={`
              border-2 border-dashed rounded-lg p-16 text-center cursor-pointer transition-colors
              ${isDragging 
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                : 'border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600'
              }
              ${loading ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*"
              onChange={handleFileInputChange}
              className="hidden"
              disabled={loading}
            />
            <input
              ref={folderInputRef}
              type="file"
              // @ts-expect-error - webkitdirectory is a valid HTML attribute but not in TypeScript types
              webkitdirectory=""
              multiple
              onChange={handleFolderInputChange}
              className="hidden"
              disabled={loading}
            />
            
            {loading ? (
              <div className="space-y-4">
                <div className="text-lg text-zinc-600 dark:text-zinc-400">Processing...</div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
                  Drop images here or click to upload
                </div>
                <div className="text-sm text-zinc-600 dark:text-zinc-400">
                  Supports: PNG, JPEG, GIF, BMP, TIFF
                </div>
                <div className="pt-4">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleFolderClick();
                    }}
                    className="px-4 py-2 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-200 dark:hover:bg-zinc-700 text-sm"
                  >
                    Or upload folder
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-4 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded text-red-700 dark:text-red-400">
              {error}
              <button
                onClick={() => setError(null)}
                className="ml-4 text-red-500 hover:text-red-700"
              >
                ×
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
