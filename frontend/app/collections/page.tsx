'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import CollectionCard from '@/components/collections/CollectionCard';
import { useCollections } from '@/hooks/useCollections';
import TopBar from '@/components/home/TopBar';
import { createQuickProcessCollection } from '@/utils/home/collection';

export default function CollectionsPage() {
  const router = useRouter();
  const { collections, isLoading, isError, error, refetch } = useCollections();

  const handleCreate = async () => {
    try {
      const collectionId = await createQuickProcessCollection();
      router.push(`/collection/${collectionId}`);
    } catch (err) {
      console.error('Failed to create collection', err);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <TopBar onCreateCollection={handleCreate} loading={false} />
      <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
              Collections
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Pick a collection to view its images and past runs.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => refetch()}
              className="px-3 py-2 text-sm rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-200 dark:hover:bg-zinc-700"
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={handleCreate}
              className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
            >
              New collection
            </button>
          </div>
        </div>

        {isLoading && (
          <div className="grid gap-4 sm:grid-cols-2">
            {[1, 2, 3, 4].map((key) => (
              <div
                key={key}
                className="h-24 rounded-lg bg-zinc-200 dark:bg-zinc-800 animate-pulse"
              />
            ))}
          </div>
        )}

        {isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 text-red-700 p-4">
            Failed to load collections: {error?.message || 'Unknown error'}
          </div>
        )}

        {!isLoading && !isError && collections.length === 0 && (
          <div className="rounded-lg border border-dashed border-zinc-300 dark:border-zinc-700 p-8 text-center text-zinc-600 dark:text-zinc-400">
            <p className="text-lg font-medium">No collections yet.</p>
            <p className="text-sm mt-1">
              Create one to start uploading images and running models.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <button
                type="button"
                onClick={handleCreate}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Create collection
              </button>
              <Link
                href="/"
                className="px-4 py-2 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-200 dark:hover:bg-zinc-700"
              >
                Go to upload
              </Link>
            </div>
          </div>
        )}

        {!isLoading && !isError && collections.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2">
            {collections.map((collection) => (
              <CollectionCard
                key={collection.collection_id}
                collection={collection}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
