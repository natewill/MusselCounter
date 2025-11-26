import { createCollection } from '@/lib/api';

export async function createQuickProcessCollection() {
  const name = `Quick Process - ${new Date().toLocaleString()}`;
  const response = await createCollection(name, null);
  return response.collection_id;
}
