/**
 * Tests for image utility functions
 */
import { describe, it, expect } from 'vitest'
import { filterNonDuplicateIds } from '@/utils/imageUtils'

describe('filterNonDuplicateIds', () => {
  it('should filter out duplicate IDs', () => {
    const uploadedIds = [1, 2, 3, 4, 5]
    const duplicateIds = [2, 4]
    const result = filterNonDuplicateIds(uploadedIds, duplicateIds)

    expect(result).toEqual([1, 3, 5])
  })

  it('should return all IDs when no duplicates exist', () => {
    const uploadedIds = [1, 2, 3]
    const duplicateIds: number[] = []
    const result = filterNonDuplicateIds(uploadedIds, duplicateIds)

    expect(result).toEqual([1, 2, 3])
  })

  it('should return empty array when all are duplicates', () => {
    const uploadedIds = [1, 2, 3]
    const duplicateIds = [1, 2, 3]
    const result = filterNonDuplicateIds(uploadedIds, duplicateIds)

    expect(result).toEqual([])
  })

  it('should handle empty uploaded IDs array', () => {
    const uploadedIds: number[] = []
    const duplicateIds = [1, 2, 3]
    const result = filterNonDuplicateIds(uploadedIds, duplicateIds)

    expect(result).toEqual([])
  })

  it('should preserve order of non-duplicate IDs', () => {
    const uploadedIds = [5, 3, 7, 1, 9]
    const duplicateIds = [3, 9]
    const result = filterNonDuplicateIds(uploadedIds, duplicateIds)

    expect(result).toEqual([5, 7, 1])
  })
})
