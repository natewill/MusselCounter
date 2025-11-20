import { useRouter } from 'next/navigation';
import {FaSearch} from 'react-icons/fa'

export default function SearchBar() {
  const router = useRouter();

  return(
    <div className="bgw-full max-w-md bg-white dark:bg-zinc-900 rounded-lg p-4 pr-20 border border-zinc-200 dark:border-zinc-800">
        <FaSearch className="text-violet-500 cursor-pointer"/>
        <input type="text" placeholder="Search Collection Name..." 
        className ="bg-transparent border-none outline-none text-zinc-600 dark:text-zinc-400"/>
    </div>

  );
}
