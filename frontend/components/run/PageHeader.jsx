import { useRouter } from 'next/navigation';
import AddModelButton from './AddModelButton';

export default function PageHeader({ batchName, children }) {
  const router = useRouter();

  return (
    <div className="mb-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <button
            onClick={() => router.push('/')}
            className="mb-2 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            ← Back to Home
          </button>
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">
            Run Results
          </h1>
          {batchName && (
            <p className="text-zinc-600 dark:text-zinc-400 mt-2">Batch: {batchName}</p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <AddModelButton />
          {children && (
            <div>
              {children}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

