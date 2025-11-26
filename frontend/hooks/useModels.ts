import { useState, useEffect, useRef } from 'react';
import { getModels } from '@/lib/api';

export function useModels(initialModelId?: number | null) {
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const defaultModelSetRef = useRef(false);

  // Apply initial model (e.g., from URL) before defaults run
  useEffect(() => {
    if (initialModelId && !defaultModelSetRef.current) {
      setSelectedModelId(initialModelId);
      defaultModelSetRef.current = true;
    }
  }, [initialModelId]);

  const loadModels = () => {
    getModels()
      .then((data) => {
        setModels(data);
        // Set default model if none is selected and we haven't set it yet
        if (
          data.length > 0 &&
          !defaultModelSetRef.current &&
          selectedModelId === null &&
          data[0] &&
          data[0].model_id
        ) {
          setSelectedModelId(data[0].model_id);
          defaultModelSetRef.current = true;
        }
      })
      .catch((err) => {
        console.error('Failed to load models:', err);
      });
  };

  useEffect(() => {
    loadModels();
    
    // Listen for model updates
    const handleModelsUpdated = () => {
      loadModels();
    };
    window.addEventListener('modelsUpdated', handleModelsUpdated);
    
    return () => {
      window.removeEventListener('modelsUpdated', handleModelsUpdated);
    };
  }, []);

  return { models, selectedModelId, setSelectedModelId };
}
