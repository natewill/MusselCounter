'use client';

import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { uploadModel } from '@/lib/api';

export default function AddModelButton({ onSuccess }) {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const queryClient = useQueryClient();

  const handleFileChange = async (e) => {
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
      setError(errorMsg);
      return;
    }

    setUploading(true);
    setError(null);
    onSuccess?.(null);

    try {
      const result = await uploadModel(file);
      
      // Invalidate models query to refresh the list (for any components using React Query)
      await queryClient.invalidateQueries({ queryKey: ['models'] });
      
      // Dispatch custom event to trigger refresh in useModels hook
      window.dispatchEvent(new CustomEvent('modelsUpdated'));
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      // Show success message
      onSuccess?.(`Model "${result.name}" uploaded successfully!`);
    } catch (err) {
      console.error('[AddModelButton] Upload failed:', {
        error: err,
        message: err.message,
        response: err.response,
        responseData: err.response?.data,
        status: err.response?.status,
        statusText: err.response?.statusText
      });
      const errorMsg = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to upload model';
      setError(errorMsg);
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
        disabled={uploading}
      />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-2"
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
          '+ Add Model'
        )}
      </button>
      {error && (
        <div className="absolute top-full mt-1 right-0 text-red-600 dark:text-red-400 text-sm whitespace-nowrap bg-white dark:bg-zinc-900 px-2 py-1 rounded shadow z-10">
          {error}
        </div>
      )}
    </div>
  );
}
