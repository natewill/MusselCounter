'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function LegacyCollectionPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/collections');
  }, [router]);

  return <div className="min-h-screen p-8 text-zinc-700 dark:text-zinc-300">Redirecting to history...</div>;
}
