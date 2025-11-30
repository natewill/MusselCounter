import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function SearchBar() {

  const [input, setInput] = useState("")

  return(
    <div>
      <div className="bgw-full max-w-md bg-white dark:bg-zinc-900 rounded-lg p-4 pr-20 border border-zinc-200 dark:border-zinc-800 mt-4">
          <span 
          className="text-zinc-500 text-xl">🔍
          </span>
          <input 
            type="text" 
            placeholder="Search Collection Name..." 
            className ="bg-transparent border-none outline-none text-zinc-600 dark:text-zinc-400"
            value={input}
            onChange={(tx) => setInput(tx.target.value)}
          />
      </div>
      
    </div>

  );
}
