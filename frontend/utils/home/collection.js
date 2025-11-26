import { createCollection } from '@/lib/api';
import { safeSetItem } from '@/utils/storage';

export async function createQuickProcessCollection(setActiveCollectionId) {
  const name = `Quick Process - ${new Date().toLocaleString()}`;
  const response = await createCollection(name, null);
  const collectionId = response.collection_id;
  setActiveCollectionId(collectionId);
  await safeSetItem('quickProcessCollectionId', collectionId.toString());
  return collectionId;
}
