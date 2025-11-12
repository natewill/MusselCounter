'use client';

import { Component, ReactNode } from 'react';
import { ErrorBoundary as ReactErrorBoundary, FallbackProps } from 'react-error-boundary';
import { useRouter } from 'next/navigation';

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold text-red-800 dark:text-red-200 mb-2">
            Something went wrong
          </h2>
          <p className="text-red-600 dark:text-red-400 text-sm mb-4">
            {error.message || 'An unexpected error occurred'}
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={resetErrorBoundary}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
            >
              Try again
            </button>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded hover:bg-zinc-300 dark:hover:bg-zinc-700 transition-colors"
            >
              Go to Home
            </button>
          </div>
        </div>
        {process.env.NODE_ENV === 'development' && (
          <details className="mt-4 text-left">
            <summary className="cursor-pointer text-sm text-zinc-600 dark:text-zinc-400">
              Error details (dev only)
            </summary>
            <pre className="mt-2 p-4 bg-zinc-100 dark:bg-zinc-900 rounded text-xs overflow-auto max-h-64">
              {error.stack}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}

interface ErrorBoundaryProps {
  children: ReactNode;
}

export default function ErrorBoundary({ children }: ErrorBoundaryProps) {
  return (
    <ReactErrorBoundary
      FallbackComponent={ErrorFallback}
      onError={(error, errorInfo) => {
        // Log error for monitoring (could send to Sentry, etc.)
        console.error('Error caught by boundary:', error, errorInfo);
      }}
      onReset={() => {
        // Clear any error state when reset
        window.location.reload();
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
}

