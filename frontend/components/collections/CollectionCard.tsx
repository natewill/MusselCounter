import Link from 'next/link';
import { CollectionSummary } from '@/hooks/useCollections';

interface Props {
  collection: CollectionSummary;
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

export default function CollectionCard({ collection }: Props) {
  return (
    <Link
      href={`/collection/${collection.collection_id}`}
      className="block rounded-lg border border-zinc-200 dark:border-zinc-800 p-4 bg-white dark:bg-zinc-900 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm text-zinc-500 dark:text-zinc-400">
            #{collection.collection_id}
          </div>
          <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
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
          <div className="text-xs text-zinc-500 dark:text-zinc-500">
            Created {formatDate(collection.created_at)}
          </div>
        </div>
      </div>
    </Link>
  );
}
