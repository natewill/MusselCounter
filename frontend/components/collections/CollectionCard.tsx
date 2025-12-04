import Link from 'next/link';
import { CollectionSummary } from '@/hooks/useCollections';

interface Props {
  collection: CollectionSummary;
  onDelete?: (id: number) => void;
  deleting?: boolean;
  onEditName?: (id: number) => void;
  renaming?: boolean;
  renameValue?: string;
  onRenameChange?: (value: string) => void;
  onRenameSave?: () => void;
  onRenameCancel?: () => void;
}

function getImageUrl(storedPath?: string | null) {
  if (!storedPath) return null;
  const filename = storedPath.split('/').pop();
  if (!filename) return null;
  return `http://127.0.0.1:8000/uploads/${filename}`;
}

function formatDate(dateString: string) {
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return dateString;
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function getStatusBadge(status?: string | null) {
  if (!status) return null;

  const statusConfig: Record<string, { label: string; className: string }> = {
    pending: { label: 'Pending', className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' },
    running: { label: 'Running', className: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
    completed: { label: 'Completed', className: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' },
    failed: { label: 'Failed', className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' },
    cancelled: { label: 'Cancelled', className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' },
  };

  const config = statusConfig[status] || { label: status, className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' };

  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${config.className}`}>
      {config.label}
    </span>
  );
}

export default function CollectionCard({
  collection,
  onDelete,
  deleting = false,
  onEditName,
  renaming = false,
  renameValue = '',
  onRenameChange,
  onRenameSave,
  onRenameCancel,
  onOpen,
}: Props) {
  const imageUrl = getImageUrl(collection.first_image_path);
  return (
    <Link
      href={`/collection/${collection.collection_id}`}
      className="relative block rounded-lg border border-zinc-200 dark:border-zinc-800 p-7 bg-white dark:bg-zinc-900 shadow-sm hover:shadow-md hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors transition-shadow h-full"
      id={`image-card-${collection.collection_id}`}
      onClick={() => onOpen?.(collection.collection_id)}
    >
      {onDelete && (
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete(collection.collection_id);
          }}
          disabled={deleting}
          className={`absolute top-3 right-3 p-2 rounded bg-white/90 dark:bg-zinc-800/90 backdrop-blur-sm border border-zinc-200 dark:border-zinc-700 shadow ${
            deleting
              ? 'text-zinc-400 dark:text-zinc-600 cursor-not-allowed'
              : 'text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300'
          }`}
          title={deleting ? 'Deleting...' : 'Delete collection'}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
      <div className="flex flex-col gap-6 h-full">
        <div className="flex items-start gap-4">
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="text-sm text-zinc-500 dark:text-zinc-400">
              #{collection.collection_id}
            </div>
            <div className="flex items-center gap-2">
              {renaming ? (
                <>
                  <input
                    value={renameValue}
                    onChange={(e) => onRenameChange?.(e.target.value)}
                    onClick={(e) => e.preventDefault()}
                    className="px-2 py-1 text-sm border border-zinc-300 dark:border-zinc-600 rounded bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    autoFocus
                  />
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onRenameSave?.();
                    }}
                    className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onRenameCancel?.();
                    }}
                    className="px-2 py-1 text-xs bg-zinc-200 dark:bg-zinc-700 text-zinc-800 dark:text-zinc-200 rounded hover:bg-zinc-300 dark:hover:bg-zinc-600"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <h3 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                    {collection.name || 'Untitled collection'}
                  </h3>
                  {onEditName && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onEditName(collection.collection_id);
                      }}
                      disabled={renaming || deleting}
                      className={`p-1 text-zinc-600 dark:text-zinc-300 hover:text-blue-600 dark:hover:text-blue-400 ${
                        renaming || deleting ? 'opacity-50 cursor-not-allowed' : ''
                      }`}
                      title="Edit collection name"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                  )}
                </>
              )}
            </div>
            {collection.description && (
              <p className="text-sm text-zinc-600 dark:text-zinc-400 line-clamp-2">
                {collection.description}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2 pt-2 text-sm items-center">
              <span className="px-3 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-700">
                {collection.image_count} images
              </span>
              {collection.live_mussel_count !== undefined && collection.live_mussel_count !== null && (
                <span className="px-3 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 flex items-center gap-2">
                  <span>{collection.live_mussel_count} live mussels</span>
                  {getStatusBadge(collection.latest_run_status)}
                </span>
              )}
              <span className="text-xs text-zinc-500 dark:text-zinc-400 ml-auto">
                Created {formatDate(collection.created_at)}
              </span>
            </div>
          </div>
        </div>
        <div className="mt-auto">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0" />
          </div>
          <div className="overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-800 h-64 flex items-center justify-center">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={collection.name || 'Collection preview'}
                className="h-64 w-full object-cover"
                loading="lazy"
              />
            ) : (
              <svg className="w-10 h-10 text-zinc-400 dark:text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
