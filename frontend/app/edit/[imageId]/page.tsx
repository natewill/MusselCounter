'use client';

import Link from 'next/link';

export default function LegacyEditPage() {
  return (
    <div className="min-h-screen p-8 text-zinc-700 dark:text-zinc-300">
      <p className="mb-4">This legacy route moved.</p>
      <Link href="/collections" className="text-blue-600 hover:underline">
        Go to History
      </Link>
    </div>
  );
}
