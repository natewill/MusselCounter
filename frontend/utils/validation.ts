// File validation constants
export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB per file
export const MAX_TOTAL_SIZE = 500 * 1024 * 1024; // 500MB total per upload
export const MAX_FILES = 1000; // Maximum number of files per upload

// Valid image types
export const VALID_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff'];
export const VALID_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif'];

/**
 * Validate file type by both MIME type and extension
 */
export function isValidImageType(file: File): boolean {
  // Check MIME type
  if (file.type && VALID_IMAGE_TYPES.includes(file.type.toLowerCase())) {
    return true;
  }
  
  // Fallback: check file extension
  const fileName = file.name.toLowerCase();
  return VALID_EXTENSIONS.some(ext => fileName.endsWith(ext));
}

/**
 * Validate image files with Zod
 */
export function validateImageFiles(files: FileList | File[]): { validFiles: File[]; errors: string[] } {
  const fileArray = Array.from(files);
  const validFiles: File[] = [];
  const errors: string[] = [];
  let totalSize = 0;
  
  // Check file count limit
  if (fileArray.length > MAX_FILES) {
    errors.push(`Too many files. Maximum ${MAX_FILES} files allowed per upload.`);
    return { validFiles: [], errors };
  }
  
  for (const file of fileArray) {
    // Check if it's a File object
    if (!(file instanceof File)) {
      const fileName = (file as { name?: string }).name || 'Unknown file';
      errors.push(`"${fileName}" is not a valid file.`);
      continue;
    }
    
    // Check file type
    if (!isValidImageType(file)) {
      errors.push(`"${file.name}" is not a valid image file. Supported formats: PNG, JPEG, GIF, BMP, TIFF.`);
      continue;
    }
    
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      errors.push(`"${file.name}" is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum file size is ${MAX_FILE_SIZE / 1024 / 1024}MB.`);
      continue;
    }
    
    // Check total size
    if (totalSize + file.size > MAX_TOTAL_SIZE) {
      errors.push(`Total upload size would exceed ${MAX_TOTAL_SIZE / 1024 / 1024}MB. Please select fewer files.`);
      break;
    }
    
    validFiles.push(file);
    totalSize += file.size;
  }
  
  return { validFiles, errors };
}

/**
 * Check if threshold value is valid (0.0 to 1.0)
 * Returns true if valid, false otherwise
 */
export function isThresholdValid(threshold: number | null | undefined): boolean {
  if (threshold === null || threshold === undefined) {
    return true; // null/undefined is valid (will use default)
  }
  const thresh = Number(threshold);
  return !isNaN(thresh) && thresh >= 0.0 && thresh <= 1.0;
}

/**
 * Get validation error message for threshold, or null if valid.
 */
export const getThresholdValidationError = (
  threshold: number | string | null | undefined
): string | null => {
  if (threshold === null || threshold === undefined || threshold === '') {
    return null; // null/undefined/empty is valid (uses default)
  }

  const numericThreshold = Number(threshold);
  if (Number.isNaN(numericThreshold)) {
    return 'Threshold must be a number';
  }
  if (numericThreshold < 0.0) {
    return 'Threshold must be at least 0.0';
  }
  if (numericThreshold > 1.0) {
    return 'Threshold must be at most 1.0';
  }
  return null;
};
