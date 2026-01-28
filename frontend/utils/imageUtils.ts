/**
 * Filter out duplicate image IDs from uploaded image IDs
 * @param uploadedImageIds - Array of all uploaded image IDs
 * @param duplicateImageIds - Array of duplicate image IDs to exclude
 * @returns Array of non-duplicate image IDs
 */
export function filterNonDuplicateIds(
  uploadedImageIds: number[],
  duplicateImageIds: number[]
): number[] {
  return uploadedImageIds.filter(id => !duplicateImageIds.includes(id));
}

/**
 * Extract the filename from a stored path that may use \ or / separators.
 */
export function getStoredFilename(storedPath?: string | null): string | null {
  if (!storedPath) return null;
  const normalized = storedPath.replace(/\\/g, '/');
  const filename = normalized.split('/').pop();
  return filename || null;
}

