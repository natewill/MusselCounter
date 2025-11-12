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

