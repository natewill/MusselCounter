import Link from 'next/link';
import { CollectionSummary } from '@/hooks/useCollections';

interface Props {
  collection: CollectionSummary;
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

export default function CollectionCard({ collection }: Props) {
  const imageUrl = getImageUrl(collection.first_image_path);
  return (
    <Link
      href={`/collection/${collection.collection_id}`}
      className="block rounded-lg border border-zinc-200 dark:border-zinc-800 p-5 bg-white dark:bg-zinc-900 shadow-sm hover:shadow-md transition-shadow h-full"
      id={`image-card-${collection.collection_id}`}
    >
      <div className="flex flex-col gap-4 h-full">
        <div className="flex items-start gap-4">
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <div className="text-sm text-zinc-500 dark:text-zinc-400">
                    #{collection.collection_id}
                  </div>
                  {getStatusBadge(collection.latest_run_status)}
                </div>
                <h3 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                  {collection.name || 'Untitled collection'}
                </h3>
                {collection.description && (
                  <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400 line-clamp-2">
                    {collection.description}
                  </p>
                )}
              </div>
              <div className="text-right text-sm text-zinc-600 dark:text-zinc-400">
                <div>{collection.image_count} images</div>
                {collection.live_mussel_count !== undefined && collection.live_mussel_count !== null && (
                  <div>{collection.live_mussel_count} live mussels</div>
                )}
                <div className="text-xs text-zinc-500 dark:text-zinc-500">
                  Created {formatDate(collection.created_at)}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-auto">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0" />
          </div>
          <div className="overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-800 h-52 flex items-center justify-center">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={collection.name || 'Collection preview'}
                className="h-52 w-full object-cover"
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
