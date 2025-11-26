'use client';

interface Polygon {
  class: 'live' | 'dead';
  confidence: number;
  original_class?: string;
  manually_edited: boolean;
}

interface EditPolygonModalProps {
  isOpen: boolean;
  polygon: Polygon | null;
  polygonIndex: number | null;
  saving: boolean;
  onClose: () => void;
  onClassificationChange: (newClass: 'live' | 'dead') => void;
}

export default function EditPolygonModal({
  isOpen,
  polygon,
  polygonIndex,
  saving,
  onClose,
  onClassificationChange,
}: EditPolygonModalProps) {
  if (!isOpen || !polygon || polygonIndex === null) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div 
        className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 max-w-md w-full shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Edit Mussel #{polygonIndex + 1}
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-1">Current Classification</div>
            <div className={`text-lg font-semibold ${
              polygon.class === 'live' 
                ? 'text-green-600 dark:text-green-400' 
                : 'text-red-600 dark:text-red-400'
            }`}>
              {polygon.class.charAt(0).toUpperCase() + polygon.class.slice(1)}
            </div>
          </div>
          
          <div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-1">Manually Edited</div>
            <div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              {polygon.manually_edited ? 'Yes' : 'No'}
            </div>
          </div>
          
          <div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-1">Confidence</div>
            <div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              {(polygon.confidence * 100).toFixed(1)}% {polygon.original_class ? polygon.original_class.charAt(0).toUpperCase() + polygon.original_class.slice(1) : polygon.class.charAt(0).toUpperCase() + polygon.class.slice(1)}
            </div>
          </div>

          <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">Change Classification</div>
            <div className="flex gap-3">
              <button
                onClick={() => onClassificationChange('live')}
                disabled={saving || polygon.class === 'live'}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                  polygon.class === 'live'
                    ? 'bg-green-600 dark:bg-green-500 text-white cursor-not-allowed'
                    : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50'
                } disabled:opacity-50`}
              >
                Live
              </button>
              <button
                onClick={() => onClassificationChange('dead')}
                disabled={saving || polygon.class === 'dead'}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                  polygon.class === 'dead'
                    ? 'bg-red-600 dark:bg-red-500 text-white cursor-not-allowed'
                    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50'
                } disabled:opacity-50`}
              >
                Dead
              </button>
            </div>
          </div>

          {saving && (
            <div className="text-sm text-zinc-600 dark:text-zinc-400 text-center">
              Saving...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

