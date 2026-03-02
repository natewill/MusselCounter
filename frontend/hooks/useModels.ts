import { useState, useEffect } from 'react';
import { getModels } from '@/lib/api';

export function useModels() {
  const [models, setModels] = useState([]);

  const loadModels = () => {
    getModels()
      .then((data) => {
        setModels(data);
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

  return { models };
}
