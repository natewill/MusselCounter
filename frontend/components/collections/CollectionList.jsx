import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function CollectionList() {
  const router = useRouter();

  const [count, setCount] = useState(0)

  return(
    <div>
        <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800 mt-4">
            
            <h2 className="text-xl font-semibold mb-4 text-zinc-900 dark:text-zinc-100">
                Collections ({count})
            </h2>
            <div className="text-zinc-600 dark:text-zinc-400">
                No collections yet.
            </div>
        </div>

    </div>
  );

}