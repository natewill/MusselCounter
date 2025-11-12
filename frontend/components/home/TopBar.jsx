import ModelPicker from './ModelPicker';

export default function TopBar({ models, selectedModelId, onModelChange, onCreateCollection, loading }) {
  return (
    <div className="absolute top-4 left-4 right-4 flex justify-between items-center gap-4">
      <ModelPicker
        models={models}
        selectedModelId={selectedModelId}
        onModelChange={onModelChange}
        disabled={loading}
      />
      <button
        onClick={onCreateCollection}
        className="px-4 py-2 bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-300 dark:hover:bg-zinc-700"
        disabled={loading}
      >
        Create Collection
      </button>
    </div>
  );
}

