'use client';

interface ImageStatsPanelProps {
  imageData: {
    live_mussel_count: number;
    dead_mussel_count: number;
    total_mussel_count: number;
    live_percentage: number | null;
    model_name: string;
    model_type: string;
    threshold: number;
    processed_at: string;
    width?: number;
    height?: number;
    file_hash: string;
    created_at: string;
  };
}

export default function ImageStatsPanel({ imageData }: ImageStatsPanelProps) {
  return (
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
  );
}

