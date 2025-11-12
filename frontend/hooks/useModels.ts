import { useState, useEffect, useRef } from 'react';
import { getModels } from '@/lib/api';

export function useModels() {
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const defaultModelSetRef = useRef(false);

  useEffect(() => {
    getModels()
      .then((data) => {
        setModels(data);
        // Set default model if none is selected and we haven't set it yet
        if (data.length > 0 && !defaultModelSetRef.current && data[0] && data[0].model_id) {
          setSelectedModelId(data[0].model_id);
          defaultModelSetRef.current = true;
        }
      })
      .catch((err) => {
        console.error('Failed to load models:', err);
      });
  }, []);

  return { models, selectedModelId, setSelectedModelId };
}

