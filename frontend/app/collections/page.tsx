'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';
import CollectionCard from '@/components/collections/CollectionCard';
import { useCollections } from '@/hooks/useCollections';
import { createQuickProcessCollection } from '@/utils/home/collection';
import { deleteCollection, updateCollection } from '@/lib/api';

export default function CollectionsPage() {
  const router = useRouter();
  const { collections, isLoading, isError, error, refetch } = useCollections();
  const [searchTerm, setSearchTerm] = useState('');
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState<string>('');
  const filteredCollections = useMemo(() => {
    if (!searchTerm.trim()) return collections;
    const q = searchTerm.trim().toLowerCase();
    const fuzzyMatch = (text: string, query: string) => {
      const t = text.toLowerCase();
      if (t.includes(query)) return true;
      let ti = 0;
      for (const char of query) {
        ti = t.indexOf(char, ti);
        if (ti === -1) return false;
        ti += 1;
      }
      return true;
    };
    return collections.filter((c) => fuzzyMatch(c.name || 'untitled collection', q));
  }, [collections, searchTerm]);

  const handleCreate = async () => {
    try {
      const collectionId = await createQuickProcessCollection();
      router.push(`/collection/${collectionId}`);
    } catch (err) {
      console.error('Failed to create collection', err);
    }
  };

  const handleDelete = async (id: number) => {
    if (deletingId) return;
    setDeletingId(id);
    try {
      await deleteCollection(id);
      await refetch();
    } catch (err) {
      console.error('Failed to delete collection', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleStartRename = (id: number) => {
    if (deletingId) return;
    const current = collections.find((c) => c.collection_id === id);
    setRenameValue(current?.name || '');
    setRenamingId(id);
  };

  const handleRenameSave = async () => {
    if (renamingId === null) return;
    const trimmed = renameValue.trim();
    if (!trimmed) return;
    try {
      await updateCollection(renamingId, { name: trimmed });
      await refetch();
    } catch (err) {
      console.error('Failed to rename collection', err);
    } finally {
      setRenamingId(null);
      setRenameValue('');
    }
  };

  const handleRenameCancel = () => {
    setRenamingId(null);
    setRenameValue('');
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
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
            <div>
              <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 leading-tight">
                Collections
              </h1>
              <p className="text-base text-zinc-600 dark:text-zinc-400">
                Pick a collection to view its images and past runs.
              </p>
            </div>
            <div className="w-full sm:w-72">
              <label className="sr-only" htmlFor="collection-search">Search collections</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-3 flex items-center text-zinc-400">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </span>
                <input
                  id="collection-search"
                  type="search"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search by name"
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
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

        {!isLoading && !isError && filteredCollections.length === 0 && (
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

        {!isLoading && !isError && filteredCollections.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2">
            {filteredCollections.map((collection) => (
              <CollectionCard
                key={collection.collection_id}
                collection={collection}
                onDelete={handleDelete}
                deleting={deletingId === collection.collection_id}
                onEditName={handleStartRename}
                renaming={renamingId === collection.collection_id}
                renameValue={renamingId === collection.collection_id ? renameValue : ''}
                onRenameChange={setRenameValue}
                onRenameSave={handleRenameSave}
                onRenameCancel={handleRenameCancel}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
