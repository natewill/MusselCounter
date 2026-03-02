// Valid image types
export const VALID_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/jpg'];

/**
 * Validate file type by MIME only.
 */
export function isValidImageType(file: File): boolean {
  return Boolean(file.type && VALID_IMAGE_TYPES.includes(file.type.toLowerCase()));
}

/**
 * Keep only image-type validation for uploads.
 */
export function validateImageFiles(files: FileList | File[]): { validFiles: File[]; errors: string[] } {
  const fileArray = Array.from(files) as File[];
  const validFiles: File[] = [];
  const errors: string[] = [];

  for (const file of fileArray) {
    // Check file type
    if (!isValidImageType(file)) {
      errors.push(`"${file.name}" is not a valid image file. Supported formats: PNG, JPEG.`);
      continue;
    }

    validFiles.push(file);
  }

  return { validFiles, errors };
}
