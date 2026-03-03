'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import ModelPicker from '@/components/home/ModelPicker';
import AddModelButton from '@/components/run/AddModelButton';
import { validateImageFiles } from '@/utils/validation';
import { createRun, getRunDetail } from '@/lib/api';
import { getUploadUrl } from '@/lib/api/base';
import { useModels } from '@/hooks/useModels';

interface RunInfo {
  run_id: number;
  model_id: number;
  model_name: string;
  model_type: string;
  threshold: number;
  created_at: string;
  total_images: number;
  processed_count: number;
  live_mussel_count: number;
  error_msg?: string | null;
}

interface RunImage {
  run_image_id: number;
  filename: string;
  stored_path: string;
  live_mussel_count: number;
  dead_mussel_count: number;
  processed_at?: string | null;
  error_msg?: string | null;
}

interface RunDetailPayload {
  run: RunInfo;
  images: RunImage[];
}

function deriveStatus(run: RunInfo): 'pending' | 'running' | 'completed' | 'failed' {
  if (run.error_msg) return 'failed';
  if (!run.total_images) return 'pending';
  if (run.processed_count < run.total_images) return 'running';
  return 'completed';
}

function fileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getProgressPercent(processedCount: number, totalImages: number): number {
  if (!totalImages || totalImages <= 0) return 0;
  const raw = (processedCount / totalImages) * 100;
  return Math.max(0, Math.min(100, raw));
}

export default function Home() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { models } = useModels();

  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [threshold, setThreshold] = useState(0.5);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingRunDetails, setLoadingRunDetails] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [currentRunId, setCurrentRunId] = useState<number | null>(null);
  const [currentRunData, setCurrentRunData] = useState<RunDetailPayload | null>(null);

  useEffect(() => {
    if (selectedModelId) return;
    if (models.length > 0) {
      setSelectedModelId(models[0].model_id);
    }
  }, [models, selectedModelId]);

  useEffect(() => {
    if (!currentRunId || !currentRunData) return;
    const status = deriveStatus(currentRunData.run);
    if (status !== 'running' && status !== 'pending') return;

    const timer = window.setInterval(async () => {
      try {
        const result = await getRunDetail(currentRunId);
        setCurrentRunData(result);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to refresh run results';
        setError(message);
      }
    }, 1200);

    return () => window.clearInterval(timer);
  }, [currentRunId, currentRunData]);

  const queueFiles = (inputFiles: File[] | FileList | null) => {
    if (!inputFiles || (Array.isArray(inputFiles) ? inputFiles.length === 0 : inputFiles.length === 0)) {
      return;
    }

    const { validFiles: imageFiles, errors } = validateImageFiles(inputFiles);
    if (imageFiles.length === 0) {
      setError(errors.join(' ') || 'Please select valid image files');
      return;
    }

    setPendingFiles((prev) => {
      const seen = new Set(prev.map(fileKey));
      const next = [...prev];
      for (const file of imageFiles) {
        const key = fileKey(file);
        if (seen.has(key)) continue;
        seen.add(key);
        next.push(file);
      }
      return next;
    });
    setError(null);
    setSuccessMessage(null);
  };

  const startRun = async () => {
    if (!selectedModelId) {
      setError('Select a model before starting a run');
      return;
    }
    if (pendingFiles.length === 0) {
      setError('Add images before starting a run');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await createRun(selectedModelId, threshold, pendingFiles);
      const runId = response?.run?.run_id;
      if (!runId) {
        throw new Error('Run created but run_id missing');
      }

      setCurrentRunId(runId);
      setPendingFiles([]);
      setLoadingRunDetails(true);

      const detail = await getRunDetail(runId);
      setCurrentRunData(detail);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create run. Please try again.';
      setError(message);
    } finally {
      setLoading(false);
      setLoadingRunDetails(false);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    queueFiles(e.target.files);
    e.target.value = '';
  };

  const handleAddImages = () => {
    if (loading) return;
    fileInputRef.current?.click();
  };

  const handleDeleteAllImages = () => {
    if (loading) return;
    setPendingFiles([]);
  };

  const run = currentRunData?.run ?? null;
  const runImages = currentRunData?.images ?? [];
  const runStatus = run ? deriveStatus(run) : null;
  const canEditCurrentRun = runStatus === 'completed';
  const runProgressPercent = run ? getProgressPercent(run.processed_count, run.total_images) : 0;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black text-zinc-900 dark:text-zinc-100">
      <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Run Workspace</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">Create runs here. Completed runs are saved in history.</p>
          </div>
          <Link
            href="/collections"
            className="px-3 py-2 text-sm rounded bg-zinc-200 dark:bg-zinc-700 hover:bg-zinc-300 dark:hover:bg-zinc-600"
          >
            History
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4">
          <div className="flex flex-col lg:flex-row lg:items-center gap-4 lg:gap-6">
            <ModelPicker
              models={models}
              selectedModelId={selectedModelId}
              onModelChange={setSelectedModelId}
              disabled={loading}
            />
            <AddModelButton
              onSuccess={(msg) => {
                setSuccessMessage(msg || 'Model uploaded successfully');
                setError(null);
              }}
              onError={(msg) => {
                if (msg) {
                  setError(msg);
                  setSuccessMessage(null);
                }
              }}
            />

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <label htmlFor="threshold-input" className="text-sm text-zinc-700 dark:text-zinc-300 whitespace-nowrap">
                Threshold
              </label>
              <input
                id="threshold-input"
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                disabled={loading}
                className="w-44"
              />
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300 w-12 text-right">
                {threshold.toFixed(2)}
              </span>
            </div>

            <div className="lg:ml-auto flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/png,image/jpeg"
                onChange={handleFileInputChange}
                className="hidden"
                disabled={loading}
              />
              <button
                type="button"
                onClick={handleAddImages}
                disabled={loading}
                className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                Add Images
              </button>
              <button
                type="button"
                onClick={handleDeleteAllImages}
                disabled={loading || pendingFiles.length === 0}
                className="px-3 py-2 text-sm rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                Delete All Images
              </button>
              <button
                type="button"
                onClick={startRun}
                disabled={loading || pendingFiles.length === 0 || !selectedModelId}
                className="px-3 py-2 text-sm rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {loading ? 'Starting...' : 'Start Run'}
              </button>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="text-lg font-semibold">Queued Images ({pendingFiles.length})</h2>
          </div>

          {pendingFiles.length === 0 ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">No images queued. Click Add Images to choose files.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {pendingFiles.map((file) => (
                <div
                  key={fileKey(file)}
                  className="rounded border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/40 p-3"
                >
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">{formatFileSize(file.size)}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="text-lg font-semibold">Current Run Results</h2>
            {run && <span className="text-sm text-zinc-600 dark:text-zinc-400">Run #{run.run_id}</span>}
          </div>

          {!run && !loadingRunDetails ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">No run started yet.</p>
          ) : loadingRunDetails ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">Loading run results...</p>
          ) : run ? (
            <>
              <div className="flex flex-wrap items-center gap-4 text-sm mb-4">
                <span>Status: <strong>{runStatus}</strong></span>
                <span>Processed: <strong>{run.processed_count}/{run.total_images}</strong></span>
                <span>Total live: <strong>{run.live_mussel_count}</strong></span>
              </div>
              {(runStatus === 'pending' || runStatus === 'running') && (
                <div className="mb-4">
                  <div className="h-2 w-full rounded bg-zinc-200 dark:bg-zinc-700 overflow-hidden">
                    <div
                      className="h-full bg-blue-600 dark:bg-blue-500 transition-all"
                      style={{ width: `${runProgressPercent}%` }}
                    />
                  </div>
                </div>
              )}
              {run.error_msg && (
                <p className="text-sm text-red-600 dark:text-red-400 mb-4">{run.error_msg}</p>
              )}

              {runImages.length === 0 ? (
                <p className="text-sm text-zinc-600 dark:text-zinc-400">No images in this run yet.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {runImages.map((image) => {
                    const imageUrl = getUploadUrl(image.stored_path);
                    return (
                      <div
                        key={image.run_image_id}
                        className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden"
                      >
                        {imageUrl ? (
                          <img src={imageUrl} alt={image.filename} className="w-full h-44 object-cover" />
                        ) : (
                          <div className="w-full h-44 bg-zinc-200 dark:bg-zinc-800" />
                        )}
                        <div className="p-3 space-y-1">
                          <p className="text-sm font-medium truncate">{image.filename}</p>
                          <p className="text-sm text-zinc-600 dark:text-zinc-400">
                            Live: {image.live_mussel_count} | Dead: {image.dead_mussel_count}
                          </p>
                          {image.error_msg && (
                            <p className="text-xs text-red-600 dark:text-red-400">{image.error_msg}</p>
                          )}
                          {run && (
                            <Link
                              href={`/runs/${run.run_id}/images/${image.run_image_id}`}
                              className="inline-block mt-2 px-3 py-2 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
                            >
                              {canEditCurrentRun ? 'Open / Edit' : 'Open'}
                            </Link>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : null}
        </section>

        {error && (
          <section className="rounded border border-red-300 bg-red-50 dark:bg-red-900/20 px-3 py-2 text-sm text-red-700 dark:text-red-300">
            <div className="flex items-center justify-between gap-3">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                className="px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50"
              >
                Dismiss
              </button>
            </div>
          </section>
        )}

        {successMessage && (
          <section className="rounded border border-green-300 bg-green-50 dark:bg-green-900/20 px-3 py-2 text-sm text-green-700 dark:text-green-300">
            <div className="flex items-center justify-between gap-3">
              <span>{successMessage}</span>
              <button
                type="button"
                onClick={() => setSuccessMessage(null)}
                className="px-2 py-1 rounded bg-green-100 dark:bg-green-900/30 hover:bg-green-200 dark:hover:bg-green-900/50"
              >
                Dismiss
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
