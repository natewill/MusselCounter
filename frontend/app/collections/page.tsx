'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import CollectionCard from '@/components/collections/CollectionCard';
import { useCollections } from '@/hooks/useCollections';
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
      <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="max-w-6xl mx-auto px-8 py-3 flex items-center justify-between">
          <Link
            href="/"
            className="px-3 py-2 text-sm rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-300 dark:hover:bg-zinc-600"
          >
            Home
          </Link>
          <button
            type="button"
            onClick={handleCreate}
            className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            Start New Run
          </button>
        </div>
      </div>
      <main className="max-w-6xl mx-auto px-8 pt-12 pb-10 space-y-7">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 leading-tight">
            Collections
          </h1>
          <p className="text-base text-zinc-600 dark:text-zinc-400">
            Pick a collection to view its images and past runs.
          </p>
        </div>

        {isLoading && (
          <div className="grid gap-5 sm:grid-cols-2">
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
          <div className="grid gap-5 sm:grid-cols-2">
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
