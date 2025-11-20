import { useRouter } from 'next/navigation';

export default function Title() {
  const router = useRouter();

  return(
    <div className="flex-1">
        <button
            onClick={() => router.push('/')}
            className="mb-2 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
        >
            ← Back to Home
        </button>
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">
                Colletion History
        </h1>
    </div>

  );

}