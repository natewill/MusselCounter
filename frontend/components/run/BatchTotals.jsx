export default function BatchTotals({ batch, imageCount, images }) {
  // Calculate live and dead totals from images in real-time (updates as images are processed)
  // This gives us live updates as the run progresses
  const liveCount = images?.reduce((sum, img) => sum + (img.live_mussel_count || 0), 0) || 0;
  const deadCount = images?.reduce((sum, img) => sum + (img.dead_mussel_count || 0), 0) || 0;
  
  // Use calculated totals if we have processed images, otherwise fall back to batch totals
  const displayLiveCount = images && images.length > 0 ? liveCount : (batch.live_mussel_count || 0);
  const displayDeadCount = images && images.length > 0 ? deadCount : (batch.dead_mussel_count || 0);
  
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 mb-6 border border-zinc-200 dark:border-zinc-800">
      <h2 className="text-xl font-semibold mb-4 text-zinc-900 dark:text-zinc-100">Totals</h2>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <div className="text-sm text-zinc-600 dark:text-zinc-400">Live Mussels</div>
          <div className="text-3xl font-bold text-green-600 dark:text-green-400">
            {displayLiveCount}
          </div>
        </div>
        <div>
          <div className="text-sm text-zinc-600 dark:text-zinc-400">Dead Mussels</div>
          <div className="text-3xl font-bold text-red-600 dark:text-red-400">
            {displayDeadCount}
          </div>
        </div>
        <div>
          <div className="text-sm text-zinc-600 dark:text-zinc-400">Total Images</div>
          <div className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">
            {imageCount}
          </div>
        </div>
      </div>
    </div>
  );
}

