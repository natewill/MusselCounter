export default function UploadArea({
  fileInputRef,
  folderInputRef,
  isDragging,
  loading,
  onDragOver,
  onDragLeave,
  onDrop,
  onUploadClick,
  onFolderClick,
  onFileChange,
  onFolderChange,
}) {
  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onMouseDown={(e) => {
        // If clicking a button, prevent the parent onClick from firing
        const path = e.nativeEvent.composedPath?.() || [];
        const clickedButton = path.find(
          (el) => el instanceof HTMLElement && el.tagName === 'BUTTON'
        );
        if (clickedButton) {
          e.preventDefault();
        }
      }}
      onClick={(e) => {
        // If clicking on folder input, don't trigger file picker
        if (e.target.id === 'folder-input') {
          return;
        }
        
        // Only trigger file picker if NOT clicking on a button
        const path = e.nativeEvent.composedPath?.() || [];
        const clickedButton = path.find(
          (el) => el instanceof HTMLElement && el.tagName === 'BUTTON'
        );
        if (!clickedButton) {
          onUploadClick();
        }
      }}
      className={`
        border-2 border-dashed rounded-lg p-64 text-center cursor-pointer transition-colors
        ${isDragging 
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
          : 'border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600'
        }
        ${loading ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <input
        key="file-input"
        id="file-input"
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*"
        onChange={onFileChange}
        className="hidden"
        disabled={loading}
      />
      <input
        key="folder-input"
        id="folder-input"
        ref={folderInputRef}
        type="file"
        // @ts-expect-error - webkitdirectory is a valid HTML attribute but not in TypeScript types
        webkitdirectory=""
        multiple
        onChange={onFolderChange}
        className="hidden"
        disabled={loading}
      />
      
      {loading ? (
        <div className="space-y-4">
          <div className="text-lg text-zinc-600 dark:text-zinc-400">Processing...</div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            Drop images or folders here
          </div>
          <div className="text-sm text-zinc-600 dark:text-zinc-400">
            Supports: PNG, JPEG, GIF, BMP, TIFF
          </div>
          <div className="flex gap-3 pt-4 justify-center">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onUploadClick();
              }}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Select Files
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onFolderClick();
              }}
              disabled={loading}
              className="px-4 py-2 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-200 dark:hover:bg-zinc-700 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Select Folder
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
