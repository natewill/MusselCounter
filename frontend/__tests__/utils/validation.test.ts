/**
 * Tests for validation utilities
 */
import { describe, it, expect } from 'vitest'
import {
  isValidImageType,
  validateImageFiles,
  validateThreshold,
  isThresholdValid,
  getThresholdValidationError,
  validateBatchId,
  validateModelId,
  MAX_FILE_SIZE,
  MAX_FILES,
  MAX_TOTAL_SIZE,
} from '@/utils/validation'

describe('isValidImageType', () => {
  it('should accept valid MIME types', () => {
    const file = new File(['content'], 'test.jpg', { type: 'image/jpeg' })
    expect(isValidImageType(file)).toBe(true)
  })

  it('should accept valid file extensions when MIME type is missing', () => {
    const file = new File(['content'], 'test.png', { type: '' })
    expect(isValidImageType(file)).toBe(true)
  })

  it('should reject invalid file types', () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    expect(isValidImageType(file)).toBe(false)
  })

  it('should be case insensitive', () => {
    const file = new File(['content'], 'test.PNG', { type: 'IMAGE/PNG' })
    expect(isValidImageType(file)).toBe(true)
  })
})

describe('validateImageFiles', () => {
  it('should validate a single valid image file', () => {
    const file = new File(['content'], 'test.jpg', { type: 'image/jpeg' })
    const result = validateImageFiles([file])

    expect(result.validFiles).toHaveLength(1)
    expect(result.errors).toHaveLength(0)
  })

  it('should reject files that are too large', () => {
    const largeContent = new Array(MAX_FILE_SIZE + 1000).fill('a').join('')
    const file = new File([largeContent], 'large.jpg', { type: 'image/jpeg' })
    const result = validateImageFiles([file])

    expect(result.validFiles).toHaveLength(0)
    expect(result.errors.length).toBeGreaterThan(0)
    expect(result.errors[0]).toContain('too large')
  })

  it('should reject invalid image types', () => {
    const file = new File(['content'], 'test.txt', { type: 'text/plain' })
    const result = validateImageFiles([file])

    expect(result.validFiles).toHaveLength(0)
    expect(result.errors.length).toBeGreaterThan(0)
    expect(result.errors[0]).toContain('not a valid image')
  })

  it('should reject when too many files are uploaded', () => {
    const files = Array.from({ length: MAX_FILES + 1 }, (_, i) =>
      new File(['content'], `test${i}.jpg`, { type: 'image/jpeg' })
    )
    const result = validateImageFiles(files)

    expect(result.validFiles).toHaveLength(0)
    expect(result.errors.length).toBeGreaterThan(0)
    expect(result.errors[0]).toContain('Too many files')
  })

  it('should handle mixed valid and invalid files', () => {
    const validFile = new File(['content'], 'valid.jpg', { type: 'image/jpeg' })
    const invalidFile = new File(['content'], 'invalid.txt', { type: 'text/plain' })
    const result = validateImageFiles([validFile, invalidFile])

    expect(result.validFiles).toHaveLength(1)
    expect(result.errors).toHaveLength(1)
  })
})

describe('validateThreshold', () => {
  it('should accept valid threshold values', () => {
    expect(validateThreshold(0.5)).toBe(0.5)
    expect(validateThreshold(0.0)).toBe(0.0)
    expect(validateThreshold(1.0)).toBe(1.0)
  })

  it('should accept null and undefined', () => {
    expect(validateThreshold(null)).toBeNull()
    expect(validateThreshold(undefined)).toBeNull()
  })

  it('should reject values outside 0.0-1.0 range', () => {
    expect(() => validateThreshold(-0.1)).toThrow('between 0.0 and 1.0')
    expect(() => validateThreshold(1.5)).toThrow('between 0.0 and 1.0')
  })
})

describe('isThresholdValid', () => {
  it('should return true for valid thresholds', () => {
    expect(isThresholdValid(0.5)).toBe(true)
    expect(isThresholdValid(0.0)).toBe(true)
    expect(isThresholdValid(1.0)).toBe(true)
  })

  it('should return true for null and undefined', () => {
    expect(isThresholdValid(null)).toBe(true)
    expect(isThresholdValid(undefined)).toBe(true)
  })

  it('should return false for invalid thresholds', () => {
    expect(isThresholdValid(-0.1)).toBe(false)
    expect(isThresholdValid(1.5)).toBe(false)
    expect(isThresholdValid(NaN)).toBe(false)
  })
})

describe('getThresholdValidationError', () => {
  it('should return null for valid thresholds', () => {
    expect(getThresholdValidationError(0.5)).toBeNull()
    expect(getThresholdValidationError(0.0)).toBeNull()
    expect(getThresholdValidationError(1.0)).toBeNull()
  })

  it('should return null for null, undefined, or empty string', () => {
    expect(getThresholdValidationError(null)).toBeNull()
    expect(getThresholdValidationError(undefined)).toBeNull()
    expect(getThresholdValidationError('')).toBeNull()
  })

  it('should return error message for invalid values', () => {
    expect(getThresholdValidationError(-0.1)).toContain('at least 0.0')
    expect(getThresholdValidationError(1.5)).toContain('at most 1.0')
    expect(getThresholdValidationError('abc')).toContain('must be a number')
  })
})

describe('validateBatchId', () => {
  it('should accept valid positive integers', () => {
    expect(validateBatchId(1)).toBe(1)
    expect(validateBatchId(100)).toBe(100)
    expect(validateBatchId('42')).toBe(42)
  })

  it('should reject zero and negative numbers', () => {
    expect(() => validateBatchId(0)).toThrow('Invalid batch ID')
    expect(() => validateBatchId(-1)).toThrow('Invalid batch ID')
  })

  it('should reject non-integer values', () => {
    expect(() => validateBatchId(1.5)).toThrow('Invalid batch ID')
  })
})

describe('validateModelId', () => {
  it('should accept valid positive integers', () => {
    expect(validateModelId(1)).toBe(1)
    expect(validateModelId(999)).toBe(999)
    expect(validateModelId('123')).toBe(123)
  })

  it('should reject zero and negative numbers', () => {
    expect(() => validateModelId(0)).toThrow('Invalid model ID')
    expect(() => validateModelId(-10)).toThrow('Invalid model ID')
  })

  it('should reject non-integer values', () => {
    expect(() => validateModelId(2.5)).toThrow('Invalid model ID')
  })
})
