/**
 * Utility functions for formatting user-facing messages
 */

/**
 * Format success message for image uploads
 */
export function formatUploadSuccessMessage(
  addedCount: number,
  duplicateCount: number
): string {
  let message = `${addedCount} image${addedCount === 1 ? '' : 's'} added`;
  if (duplicateCount > 0) {
    message += `, ${duplicateCount} duplicate${duplicateCount === 1 ? '' : 's'} skipped`;
  }
  message += '!';
  return message;
}

