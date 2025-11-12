export default function ErrorDisplay({ error, onDismiss }) {
  if (!error) return null;

  return (
    <div className="mt-4 p-4 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded text-red-700 dark:text-red-400">
      {error}
      <button
        onClick={onDismiss}
        className="ml-4 text-red-500 hover:text-red-700"
      >
        ×
      </button>
    </div>
  );
}

