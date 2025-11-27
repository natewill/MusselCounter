'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import TopBar from '@/components/home/TopBar';
import UploadArea from '@/components/home/UploadArea';
import ErrorDisplay from '@/components/home/ErrorDisplay';
import { createQuickProcessCollection } from '@/utils/home/collection';
import { handleFileSelect, handleDroppedItems } from '@/utils/home/files';

export default function Home() {
  const router = useRouter();
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    // Handle both files and folders using the FileSystem API
    if (e.dataTransfer.items) {
      const files = await handleDroppedItems(e.dataTransfer.items);
      if (files.length > 0) {
        handleFileSelect(files, setLoading, setError, createQuickProcessCollection, router).catch(() => {
          // Error already handled in handleFileSelect
        });
      }
    } else {
      // Fallback for older browsers
      const files = e.dataTransfer.files;
      handleFileSelect(files, setLoading, setError, createQuickProcessCollection, router).catch(() => {
        // Error already handled in handleFileSelect
      });
    }
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    handleFileSelect(files, setLoading, setError, createQuickProcessCollection, router).catch(() => {
      // Error already handled in handleFileSelect
    });
  };

  const handleUploadClick = () => {
    if (loading) return;
    fileInputRef.current?.click();
  };

  const handleFolderClick = () => {
    if (loading) return;
    folderInputRef.current?.click();
  };

  const handleFolderInputChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files, setLoading, setError, createQuickProcessCollection, router).catch(() => {
        // Error already handled in handleFileSelect
      });
    }
  };

  const handleCreateCollection = async () => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Always create a fresh collection for a new run
      const collectionId = await createQuickProcessCollection();

      // Navigate to collection page
      router.push(`/collection/${collectionId}`);
      setLoading(false);
    } catch (err) {
      console.error('Failed to create collection or navigate:', err);
      setError(err.message || 'Failed to create run. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black relative">
      <TopBar
        onCreateCollection={handleCreateCollection}
        loading={loading}
      />

      <div className="flex items-center justify-center min-h-screen p-8">
        <div className="w-full max-w-4xl">
          <UploadArea
            fileInputRef={fileInputRef}
            folderInputRef={folderInputRef}
            isDragging={isDragging}
            loading={loading}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onUploadClick={handleUploadClick}
            onFolderClick={handleFolderClick}
            onFileChange={handleFileInputChange}
            onFolderChange={handleFolderInputChange}
          />

          <ErrorDisplay error={error} onDismiss={() => setError(null)} />
        </div>
      </div>

      <footer className="absolute bottom-4 left-0 right-0 text-center text-sm text-zinc-600 dark:text-zinc-400">
        Made by Nate Williams, Austin Ashley, Fernando Gomez, Siddharth Rakshit
      </footer>
    </div>
  );
}
