'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { deleteRunById, listRuns } from '@/lib/api';

interface RunRow {
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

function deriveStatus(run: RunRow): 'pending' | 'running' | 'completed' | 'failed' {
  if (run.error_msg) return 'failed';
  if (!run.total_images) return 'pending';
  if (run.processed_count < run.total_images) return 'running';
  return 'completed';
}

export default function HistoryPage() {
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingRunId, setDeletingRunId] = useState<number | null>(null);

  const loadRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listRuns();
      setRuns(result || []);
    } catch (err) {
      setError((err as Error).message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (runs.some((run) => deriveStatus(run) === 'running' || deriveStatus(run) === 'pending')) {
        loadRuns();
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [runs]);

  const sortedRuns = useMemo(() => {
    return [...runs].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [runs]);

  const onDelete = async (runId: number) => {
    const confirmed = window.confirm('Delete this run and its uploaded files?');
    if (!confirmed) return;

    setDeletingRunId(runId);
    setError(null);
    try {
      await deleteRunById(runId);
      await loadRuns();
    } catch (err) {
      setError((err as Error).message || 'Failed to delete run');
    } finally {
      setDeletingRunId(null);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black text-zinc-900 dark:text-zinc-100">
      <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <Link
            href="/"
            className="px-3 py-2 text-sm rounded bg-zinc-200 dark:bg-zinc-700 hover:bg-zinc-300 dark:hover:bg-zinc-600"
          >
            Home
          </Link>
          <h1 className="text-2xl font-bold">History</h1>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-4">
        {error && (
          <div className="rounded border border-red-300 bg-red-50 dark:bg-red-900/20 px-3 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Loading run history...</p>
        ) : sortedRuns.length === 0 ? (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">No runs yet.</p>
        ) : (
          <div className="space-y-3">
            {sortedRuns.map((run) => {
              const status = deriveStatus(run);
              return (
                <div
                  key={run.run_id}
                  className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-medium truncate">
                        Run #{run.run_id} · {new Date(run.created_at).toLocaleString()}
                      </p>
                      <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        {run.model_name} ({run.model_type}) · threshold {Number(run.threshold).toFixed(2)}
                      </p>
                      <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        {run.processed_count}/{run.total_images} processed · live {run.live_mussel_count} · {status}
                      </p>
                      {run.error_msg && (
                        <p className="text-sm text-red-600 dark:text-red-400">{run.error_msg}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <Link
                        href={`/runs/${run.run_id}`}
                        className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
                      >
                        Open
                      </Link>
                      <button
                        type="button"
                        onClick={() => onDelete(run.run_id)}
                        disabled={deletingRunId === run.run_id || status === 'running' || status === 'pending'}
                        className="px-3 py-2 text-sm rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                      >
                        {deletingRunId === run.run_id ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
