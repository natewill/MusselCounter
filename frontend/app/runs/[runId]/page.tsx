'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { getRunDetail, recalculateRunThreshold } from '@/lib/api';
import { getUploadUrl } from '@/lib/api/base';

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

function getProgressPercent(processedCount: number, totalImages: number): number {
  if (!totalImages || totalImages <= 0) return 0;
  const raw = (processedCount / totalImages) * 100;
  return Math.max(0, Math.min(100, raw));
}

export default function RunDetailPage() {
  const params = useParams();
  const runId = Number(Array.isArray(params.runId) ? params.runId[0] : params.runId);

  const [data, setData] = useState<RunDetailPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.5);
  const [recalculating, setRecalculating] = useState(false);
  const [sortBy, setSortBy] = useState<'default' | 'live' | 'name'>('default');

  const load = async () => {
    if (!runId) return;
    setError(null);
    try {
      const result = await getRunDetail(runId);
      setData(result);
      setThreshold(result?.run?.threshold ?? 0.5);
    } catch (err) {
      setError((err as Error).message || 'Failed to load run');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    load();
  }, [runId]);

  useEffect(() => {
    if (!data) return;
    const status = deriveStatus(data.run);
    if (status !== 'running' && status !== 'pending') return;

    const timer = window.setInterval(() => {
      load();
    }, 1200);

    return () => window.clearInterval(timer);
  }, [data]);

  const run = data?.run;
  const images = data?.images ?? [];
  const status = run ? deriveStatus(run) : 'pending';
  const canEdit = status === 'completed';
  const progressPercent = run ? getProgressPercent(run.processed_count, run.total_images) : 0;

  const sortedImages = useMemo(() => {
    const next = [...images];
    if (sortBy === 'live') {
      next.sort((a, b) => b.live_mussel_count - a.live_mussel_count);
    } else if (sortBy === 'name') {
      next.sort((a, b) => a.filename.localeCompare(b.filename));
    }
    return next;
  }, [images, sortBy]);

  const onRecalculate = async () => {
    if (!run) return;
    setRecalculating(true);
    setError(null);
    try {
      await recalculateRunThreshold(run.run_id, threshold);
      await load();
    } catch (err) {
      setError((err as Error).message || 'Failed to recalculate threshold');
    } finally {
      setRecalculating(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen p-8 text-zinc-700 dark:text-zinc-300">Loading run...</div>;
  }

  if (!run) {
    return <div className="min-h-screen p-8 text-zinc-700 dark:text-zinc-300">Run not found.</div>;
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black text-zinc-900 dark:text-zinc-100">
      <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Run #{run.run_id}</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {new Date(run.created_at).toLocaleString()} · {run.model_name} ({run.model_type})
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/collections"
              className="px-3 py-2 text-sm rounded bg-zinc-200 dark:bg-zinc-700 hover:bg-zinc-300 dark:hover:bg-zinc-600"
            >
              History
            </Link>
            <Link
              href="/"
              className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
            >
              New Run
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {error && (
          <div className="rounded border border-red-300 bg-red-50 dark:bg-red-900/20 px-3 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span>Status: <strong>{status}</strong></span>
            <span>Processed: <strong>{run.processed_count}/{run.total_images}</strong></span>
            <span>Total live: <strong>{run.live_mussel_count}</strong></span>
          </div>
          {(status === 'pending' || status === 'running') && (
            <div className="mt-3">
              <div className="h-2 w-full rounded bg-zinc-200 dark:bg-zinc-700 overflow-hidden">
                <div
                  className="h-full bg-blue-600 dark:bg-blue-500 transition-all"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          )}
          {run.error_msg && (
            <p className="text-sm text-red-600 dark:text-red-400 mt-2">{run.error_msg}</p>
          )}
        </section>

        <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm font-medium">Threshold ({threshold.toFixed(2)})</label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-64"
              disabled={status === 'running' || status === 'pending' || recalculating}
            />
            <button
              type="button"
              onClick={onRecalculate}
              disabled={status === 'running' || status === 'pending' || recalculating}
              className="px-3 py-2 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {recalculating ? 'Recalculating...' : 'Recalculate'}
            </button>

            <label className="ml-auto text-sm">
              Sort:
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'default' | 'live' | 'name')}
                className="ml-2 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-2 py-1"
              >
                <option value="default">Default</option>
                <option value="live">Live count</option>
                <option value="name">Name</option>
              </select>
            </label>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Images ({images.length})</h2>
          {sortedImages.length === 0 ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">No images found for this run.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedImages.map((image) => {
                const imageUrl = getUploadUrl(image.stored_path);
                return (
                  <div
                    key={image.run_image_id}
                    className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden"
                  >
                    {imageUrl ? (
                      <img src={imageUrl} alt={image.filename} className="w-full h-48 object-cover" />
                    ) : (
                      <div className="w-full h-48 bg-zinc-200 dark:bg-zinc-800" />
                    )}
                    <div className="p-3 space-y-2">
                      <p className="text-sm font-medium truncate">{image.filename}</p>
                      <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        Live: {image.live_mussel_count} · Dead: {image.dead_mussel_count}
                      </p>
                      {image.error_msg && (
                        <p className="text-xs text-red-600 dark:text-red-400">{image.error_msg}</p>
                      )}
                      {canEdit ? (
                        <Link
                          href={`/runs/${run.run_id}/images/${image.run_image_id}`}
                          className="inline-block px-3 py-2 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
                        >
                          Open / Edit
                        </Link>
                      ) : (
                        <span className="inline-block px-3 py-2 text-xs rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300">
                          Edit disabled until completed
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
