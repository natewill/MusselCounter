export default function ModelPicker({ models, selectedModelId, onModelChange, disabled }) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor="model-select" className="text-sm text-zinc-700 dark:text-zinc-300">
        Model:
      </label>
      <select
        id="model-select"
        value={selectedModelId || ''}
        onChange={(e) => onModelChange(parseInt(e.target.value, 10))}
        disabled={disabled || models.length === 0}
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
  );
}

