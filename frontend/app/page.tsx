'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import TopBar from '@/components/home/TopBar';
import UploadArea from '@/components/home/UploadArea';
import ErrorDisplay from '@/components/home/ErrorDisplay';
import { loadModels } from '@/utils/home/models';
import { createQuickProcessCollection } from '@/utils/home/collection';
import { handleFileSelect, handleDroppedItems } from '@/utils/home/files';
import { safeGetNumber } from '@/utils/storage';

export default function Home() {
  const router = useRouter();
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeCollectionId, setActiveCollectionId] = useState(null);
  
  // Load activeCollectionId from storage on mount
  useEffect(() => {
    safeGetNumber('quickProcessCollectionId').then((storedCollectionId) => {
      if (storedCollectionId) {
        setActiveCollectionId(storedCollectionId);
      }
    });
  }, []);
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  // Load models on mount
  useEffect(() => {
    loadModels(setModels, setSelectedModelId);
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
        handleFileSelect(
          files,
          activeCollectionId,
          setActiveCollectionId,
          selectedModelId,
          setLoading,
          setError,
          createQuickProcessCollection,
          router
        ).catch(() => {
          // Error already handled in handleFileSelect
        });
      }
    } else {
      // Fallback for older browsers
      const files = e.dataTransfer.files;
      handleFileSelect(
        files,
        activeCollectionId,
        setActiveCollectionId,
        selectedModelId,
        setLoading,
        setError,
        createQuickProcessCollection,
        router
      ).catch(() => {
        // Error already handled in handleFileSelect
      });
    }
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    handleFileSelect(
      files,
      activeCollectionId,
      setActiveCollectionId,
      selectedModelId,
      setLoading,
      setError,
      createQuickProcessCollection,
      router
    ).catch(() => {
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
      handleFileSelect(
        files,
        activeCollectionId,
        setActiveCollectionId,
        selectedModelId,
        setLoading,
        setError,
        createQuickProcessCollection,
        router
      ).catch(() => {
        // Error already handled in handleFileSelect
      });
    }
  };

  const handleCreateCollection = () => {
    // Navigate to collections page (or show form - keeping it simple for now)
    try {
      router.push('/collections');
    } catch (err) {
      console.warn('Navigation failed (page may not exist yet):', err);
      setError('Collections page not available yet');
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black relative">
      <TopBar
        models={models}
        selectedModelId={selectedModelId}
        onModelChange={setSelectedModelId}
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
    </div>
  );
}
