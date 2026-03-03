'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getRunImageDetails, updateRunImageDetection } from '@/lib/api';
import { getUploadUrl } from '@/lib/api/base';
import ImageDisplay from '@/components/edit/ImageDisplay';
import FullscreenImageModal from '@/components/edit/FullscreenImageModal';
import EditPolygonModal from '@/components/edit/EditPolygonModal';

interface Polygon {
  detection_id: number;
  bbox: number[];
  class: 'live' | 'dead';
  confidence: number;
  manually_edited: boolean;
}

interface RunImageDetail {
  run_id: number;
  run_image_id: number;
  model_id: number;
  model_name: string;
  model_type: string;
  threshold: number;
  filename: string;
  stored_path: string;
  live_mussel_count: number;
  dead_mussel_count: number;
  total_mussel_count: number;
  processed_at?: string | null;
  error_msg?: string | null;
  polygons: Polygon[];
  can_edit: boolean;
}

export default function RunImageDetailPage() {
  const params = useParams();
  const runId = Number(Array.isArray(params.runId) ? params.runId[0] : params.runId);
  const runImageId = Number(
    Array.isArray(params.runImageId) ? params.runImageId[0] : params.runImageId
  );

  const [data, setData] = useState<RunImageDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingDetectionId, setSavingDetectionId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingPolygonIndex, setEditingPolygonIndex] = useState<number | null>(null);
  const [selectedPolygonIndex, setSelectedPolygonIndex] = useState<number | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const load = async () => {
    if (!runId || !runImageId) return;
    try {
      const result = await getRunImageDetails(runId, runImageId);
      setData(result);
      setError(null);
    } catch (err) {
      setError((err as Error).message || 'Failed to load image');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    load();
  }, [runId, runImageId]);

  const onClassChange = async (detectionId: number, newClass: 'live' | 'dead') => {
    if (!data?.can_edit) return;
    setSavingDetectionId(detectionId);
    setError(null);
    try {
      await updateRunImageDetection(runId, runImageId, detectionId, newClass);
      await load();
    } catch (err) {
      setError((err as Error).message || 'Failed to update detection');
    } finally {
      setSavingDetectionId(null);
    }
  };

  if (loading) {
    return <div className="min-h-screen p-8 text-zinc-700 dark:text-zinc-300">Loading image...</div>;
  }

  if (!data) {
    return <div className="min-h-screen p-8 text-zinc-700 dark:text-zinc-300">Image not found.</div>;
  }

  const imageUrl = getUploadUrl(data.stored_path);
  const filteredPolygons = data.polygons.filter((polygon) => polygon.confidence >= data.threshold);
  const selectedPolygon =
    selectedPolygonIndex !== null && filteredPolygons[selectedPolygonIndex]
      ? filteredPolygons[selectedPolygonIndex]
      : null;
  const selectedDetectionId = selectedPolygon?.detection_id ?? null;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black text-zinc-900 dark:text-zinc-100">
      <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold truncate">{data.filename}</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {data.model_name} ({data.model_type}) · threshold {data.threshold.toFixed(2)}
            </p>
          </div>
          <Link
            href={`/runs/${data.run_id}`}
            className="px-3 py-2 text-sm rounded bg-zinc-200 dark:bg-zinc-700 hover:bg-zinc-300 dark:hover:bg-zinc-600"
          >
            Back to Run
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {error && (
          <div className="rounded border border-red-300 bg-red-50 dark:bg-red-900/20 px-3 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {data.error_msg && (
          <div className="rounded border border-amber-300 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
            Processing error for this image: {data.error_msg}
          </div>
        )}

        {!data.can_edit && (
          <div className="rounded border border-zinc-300 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-800 px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300">
            Editing is disabled until the run is fully completed.
          </div>
        )}

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ImageDisplay
            imageUrl={imageUrl || ''}
            filename={data.filename}
            polygons={filteredPolygons}
            isEditMode={data.can_edit}
            editingPolygonIndex={editingPolygonIndex}
            visiblePolygons={true}
            onFullscreen={() => setIsFullscreen(true)}
            onPolygonClick={(index) => {
              if (!data.can_edit) return;
              setSelectedPolygonIndex(index);
            }}
            onPolygonHover={(index) => setEditingPolygonIndex(index)}
          />

          <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 space-y-4">
            <div className="text-sm">
              <p>Live: <strong>{data.live_mussel_count}</strong></p>
              <p>Dead: <strong>{data.dead_mussel_count}</strong></p>
              <p>Total: <strong>{data.total_mussel_count}</strong></p>
            </div>

            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Showing {filteredPolygons.length} detections above threshold {data.threshold.toFixed(2)}.
            </p>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Use the magnifier to open fullscreen. {data.can_edit ? 'Click a bounding box to change class.' : 'Editing is disabled until run completion.'}
            </p>
          </div>
        </section>

        <FullscreenImageModal
          isOpen={isFullscreen}
          imageUrl={imageUrl || ''}
          filename={data.filename}
          polygons={filteredPolygons}
          isEditMode={data.can_edit}
          editingPolygonIndex={editingPolygonIndex}
          visiblePolygons={true}
          onClose={() => setIsFullscreen(false)}
          onPolygonClick={(index) => {
            if (!data.can_edit) return;
            setSelectedPolygonIndex(index);
            setIsFullscreen(false);
          }}
          onPolygonHover={(index) => setEditingPolygonIndex(index)}
        />

        <EditPolygonModal
          isOpen={selectedPolygonIndex !== null}
          polygon={selectedPolygon}
          polygonIndex={selectedPolygonIndex}
          saving={savingDetectionId !== null}
          onClose={() => setSelectedPolygonIndex(null)}
          onClassificationChange={(newClass) => {
            if (selectedDetectionId !== null) {
              onClassChange(selectedDetectionId, newClass);
            }
          }}
        />
      </main>
    </div>
  );
}
