'use client';

export default function ThresholdControl({ threshold, onThresholdChange, onStartNewRun, disabled, models, selectedModelId, onModelChange, imageCount, isRecalculating, hasRecalculatedData }) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Run Settings</h2>
        {isRecalculating && (
          <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
            Recalculating...
          </span>
        )}
        {!isRecalculating && hasRecalculatedData && (
          <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded">
            Using recalculated counts
          </span>
        )}
      </div>
      <div className="space-y-4">
        {/* Model Picker */}
        <div className="flex items-center gap-4">
          <label htmlFor="model-select" className="text-sm font-medium text-zinc-700 dark:text-zinc-300 w-20">
            Model:
          </label>
          <select
            id="model-select"
            value={selectedModelId || ''}
            onChange={(e) => onModelChange(parseInt(e.target.value, 10))}
            disabled={models.length === 0}
            className="flex-1 px-3 py-2 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-300 dark:border-zinc-600 rounded hover:bg-zinc-50 dark:hover:bg-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
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

        {/* Threshold Input */}
        <div className="flex items-center gap-4">
          <label htmlFor="threshold-input" className="text-sm font-medium text-zinc-700 dark:text-zinc-300 w-20">
            Threshold:
          </label>
          <div className="flex-1 flex items-center gap-4">
            <input
              id="threshold-input"
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={threshold}
              onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
              disabled={imageCount === 0}
              className="flex-1 h-2 bg-zinc-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <input
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={threshold}
              onChange={(e) => {
                const value = parseFloat(e.target.value);
                if (!isNaN(value) && value >= 0 && value <= 1) {
                  onThresholdChange(value);
                }
              }}
              disabled={imageCount === 0}
              className="w-20 px-2 py-1 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-300 dark:border-zinc-600 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>

        {/* Start New Run Button */}
        <div className="pt-2 mt-auto">
          <button
            onClick={onStartNewRun}
            disabled={disabled}
            className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            title={disabled && imageCount === 0 ? 'Upload images before starting a run' : undefined}
          >
            Start New Run with These Settings
          </button>
          {disabled && imageCount === 0 && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2 text-center">
              Upload images to start a run
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

