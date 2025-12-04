import { useRouter } from 'next/navigation';

export default function TopBar({ onCreateCollection, loading }) {
  const router = useRouter();

  return (
    <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <button
          onClick={() => router.push('/collections')}
          className="px-3 py-2 text-sm rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-300 dark:hover:bg-zinc-600"
        >
          View Collections
        </button>
        <button
          onClick={onCreateCollection}
          className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
          disabled={loading}
        >
          Start New Run
        </button>
      </div>
    </div>
  );
}

