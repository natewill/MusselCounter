export default function UploadProgress() {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 mb-6 border border-zinc-200 dark:border-zinc-800">
      <div className="space-y-2">
        <div className="flex justify-between items-center text-sm">
          <span className="text-zinc-600 dark:text-zinc-400 font-medium">
            Uploading images...
          </span>
          <span className="text-zinc-600 dark:text-zinc-400">
            Please wait
          </span>
        </div>
        <div className="w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-4 overflow-hidden relative">
          <div className="bg-blue-600 h-4 rounded-full animate-pulse" style={{ width: '100%' }} />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
        </div>
      </div>
    </div>
  );
}

