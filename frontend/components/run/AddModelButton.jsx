'use client';

import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { uploadModel } from '@/lib/api';

export default function AddModelButton({ onSuccess, onError }) {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedModelType, setSelectedModelType] = useState('YOLO');
  const [modelName, setModelName] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const queryClient = useQueryClient();

  const resetForm = () => {
    setSelectedModelType('YOLO');
    setModelName('');
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const closeModal = () => {
    if (uploading) return;
    setIsOpen(false);
    resetForm();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }

    // Validate file type
    const validExtensions = ['.pt', '.pth', '.ckpt'];
    const fileExt = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!validExtensions.includes(fileExt)) {
      const errorMsg = `Invalid file type. Supported: ${validExtensions.join(', ')}`;
      console.error('[AddModelButton] Validation failed:', errorMsg);
      onError?.(errorMsg);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      onError?.('Please choose a model file first.');
      return;
    }

    setUploading(true);
    onError?.(null);
    onSuccess?.(null);

    try {
      const result = await uploadModel(
        selectedFile,
        selectedModelType,
        modelName.trim() || undefined
      );
      
      // Invalidate models query to refresh the list (for any components using React Query)
      await queryClient.invalidateQueries({ queryKey: ['models'] });
      
      // Dispatch custom event to trigger refresh in useModels hook
      window.dispatchEvent(new CustomEvent('modelsUpdated'));
      
      // Show success message
      onSuccess?.(`Model "${result.name}" uploaded successfully!`);
      setIsOpen(false);
      resetForm();
    } catch (err) {
      let errorMsg = 'Failed to upload model';
      if (err?.response?.data?.detail) {
        errorMsg = err.response.data.detail;
      } else if (err?.response?.data?.message) {
        errorMsg = err.response.data.message;
      } else if (err?.message) {
        errorMsg = err.message;
      }
      console.error('[AddModelButton] Upload failed:', errorMsg);
      if (onError) {
        onError(errorMsg);
      }
      setIsOpen(false);
      resetForm();
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="relative">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pt,.pth,.ckpt"
        onChange={handleFileChange}
        className="hidden"
        disabled={uploading || !isOpen}
      />
      <button
        onClick={() => setIsOpen(true)}
        disabled={uploading || isOpen}
        className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-2"
      >
        + Add Model
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={closeModal}
        >
          <div
            className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 max-w-md w-full shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                Add Model
              </h2>
              <button
                onClick={closeModal}
                className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-600 dark:text-zinc-400 mb-1">
                  Model Type
                </label>
                <select
                  value={selectedModelType}
                  onChange={(e) => setSelectedModelType(e.target.value)}
                  disabled={uploading}
                  className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 rounded text-sm text-zinc-900 dark:text-zinc-100"
                >
                  <option value="YOLO">YOLO</option>
                  <option value="FASTRCNN">Faster R-CNN</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-zinc-600 dark:text-zinc-400 mb-1">
                  Model Name (optional)
                </label>
                <input
                  type="text"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="e.g. YOLO Mussel v2"
                  disabled={uploading}
                  className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 rounded text-sm text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-600 dark:text-zinc-400 mb-1">
                  Model File
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    className="px-3 py-2 bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-300 dark:hover:bg-zinc-600 text-sm"
                  >
                    Choose File
                  </button>
                  <span className="text-sm text-zinc-600 dark:text-zinc-400 truncate">
                    {selectedFile?.name || 'No file selected'}
                  </span>
                </div>
              </div>

              <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={uploading}
                  className="px-3 py-2 bg-zinc-200 dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-300 dark:hover:bg-zinc-600 text-sm disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleUpload}
                  disabled={uploading || !selectedFile}
                  className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {uploading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Uploading...</span>
                    </>
                  ) : (
                    'Upload Model'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
