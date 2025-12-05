'use client';

import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { uploadModel } from '@/lib/api';

export default function AddModelButton({ onSuccess, onError }) {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
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
      onError?.(errorMsg);
      return;
    }

    setUploading(true);
    onError?.(null);
    onSuccess?.(null);

    try {
      const result = await uploadModel(file);
      
      // Invalidate models query to refresh the list (for any components using React Query)
      await queryClient.invalidateQueries({ queryKey: ['models'] });
      
      // Dispatch custom event to trigger refresh in useModels hook
      window.dispatchEvent(new CustomEvent('modelsUpdated'));
      
      // Show success message
      onSuccess?.(`Model "${result.name}" uploaded successfully!`);
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
    } finally {
      setUploading(false);
      // Always reset file input so selecting the same file triggers onChange again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
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
        className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-2"
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
    </div>
  );
}
