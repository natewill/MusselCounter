export default function LoadingState() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
      <div className="w-full max-w-md px-8">
        <div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-4 text-center">
          Loading run data...
        </div>
        <div className="w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-3 overflow-hidden">
          <div className="bg-blue-600 h-3 rounded-full animate-pulse" style={{ width: '100%' }} />
        </div>
        <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-2 text-center">
          Please wait
        </div>
      </div>
    </div>
  );
}

