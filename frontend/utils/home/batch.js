/**
 * Batch creation utilities for home page
 */
import { createBatch } from '@/lib/api';
import { safeSetItem } from '@/utils/storage';

export async function createQuickProcessBatch(setActiveBatchId) {
  const batchName = `Quick Process - ${new Date().toLocaleString()}`;
  const batchResponse = await createBatch(batchName, null);
  const batchId = batchResponse.batch_id;
  setActiveBatchId(batchId);
  await safeSetItem('quickProcessBatchId', batchId.toString());
  console.log('Quick Process batch created:', batchId);
  return batchId;
}

