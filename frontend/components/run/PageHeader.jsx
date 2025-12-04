import { useRouter } from 'next/navigation';
import AddModelButton from './AddModelButton';

export default function PageHeader({ collectionName, children, onModelSuccess, onModelError }) {
  const router = useRouter();

  return (
    <>
      <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 mb-6">
        <div className="max-w-6xl mx-auto px-8 py-3 flex items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => router.push('/')}
              className="px-3 py-2 text-sm rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-300 dark:hover:bg-zinc-600"
            >
              Home
            </button>
            <button
              onClick={() => router.push('/collections')}
              className="px-3 py-2 text-sm rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-300 dark:hover:bg-zinc-600"
            >
              View Collections
            </button>
          </div>
          <div className="flex items-center gap-2">
            <AddModelButton onSuccess={onModelSuccess} onError={onModelError} />
            {children && (
              <div>
                {children}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
