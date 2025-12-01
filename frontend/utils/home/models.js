/**
 * Model loading utilities for home page
 */
import { getModels } from '@/lib/api';
/**
 * Load models from the backend and set the models and optionally selected model id
 * @param {*} setModels - function to set the models
 * @param {*} setSelectedModelId - optional function to set the selected model id
 * @returns - the models list
 * @throws {Error} If the request fails
 */
export async function loadModels(setModels, setSelectedModelId = null) {
  try {
    const modelsList = await getModels();

    if (modelsList && modelsList.length > 0) {
      setModels(modelsList);
      if (setSelectedModelId) {
        setSelectedModelId(modelsList[0].model_id);
      }
      return modelsList;
    } else {
      // No models available - disable processing
      setModels([]);
      if (setSelectedModelId) {
        setSelectedModelId(null);
      }
      console.warn('No models found - processing disabled until models are configured');
      return [];
    }
  } catch (err) {
    console.warn('Failed to load models (backend may not be running):', err);
    // Set to null to disable processing until backend is available
    setModels([]);
    if (setSelectedModelId) {
      setSelectedModelId(null);
    }
    return [];
  }
}

