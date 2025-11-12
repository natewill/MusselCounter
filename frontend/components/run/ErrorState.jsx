import { useRouter } from 'next/navigation';

export default function ErrorState({ error }) {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
      <div className="text-center">
        <div className="text-red-600 dark:text-red-400 mb-4">{error}</div>
        <button
          onClick={() => router.push('/')}
          className="px-4 py-2 bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-300 dark:hover:bg-zinc-700"
        >
          Go to Home
        </button>
      </div>
    </div>
  );
}

