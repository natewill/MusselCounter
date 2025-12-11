'use client';

import { useState, useRef, useEffect } from 'react';
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
  const [showWarning, setShowWarning] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const acknowledged = localStorage.getItem('disclaimerAccepted');
    setShowWarning(!acknowledged);
  }, []);

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

  const handleAcknowledge = () => {
    localStorage.setItem('disclaimerAccepted', 'true');
    setShowWarning(false);
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <TopBar
        onCreateCollection={handleCreateCollection}
        loading={loading}
      />

      {showWarning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl ring-1 ring-black/10 dark:bg-zinc-900 dark:ring-white/10">
            <p className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Disclaimer</p>
            <p className="mt-3 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
              This tool, and the model it was built for use with, were developed specifically for juvenile <em>lampsilis cardium</em> under controlled imaging conditions.
              Use outside these conditions may yield inaccurate results and should be interpreted with caution.
            </p>
            <div className="mt-6 flex justify-end">
              <button
                type="button"
                className="rounded-md bg-black px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-black dark:bg-white dark:text-black dark:hover:bg-zinc-200 dark:focus-visible:outline-white"
                onClick={handleAcknowledge}
              >
                I understand
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-start justify-center px-8 pt-24 pb-12" style={{ minHeight: 'calc(100vh - 180px)' }}>
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
