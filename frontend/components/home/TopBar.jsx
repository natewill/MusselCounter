export default function TopBar({ onCreateCollection, loading }) {
  return (
    <div className="absolute top-4 left-4 right-4 flex justify-end items-center gap-4">
      <button
        onClick={onCreateCollection}
        className="px-4 py-2 bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-300 dark:hover:bg-zinc-700"
        disabled={loading}
      >
        Start New Run
      </button>
    </div>
  );
}

