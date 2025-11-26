import { useState, useEffect } from 'react';

interface ImageScale {
  scaleX: number;
  scaleY: number;
}

interface UseImageScaleProps {
  imageRef: React.RefObject<HTMLImageElement>;
  imageData: { width?: number; height?: number } | null;
  enabled?: boolean;
}

export function useImageScale({ imageRef, imageData, enabled = true }: UseImageScaleProps): ImageScale {
  const [scale, setScale] = useState<ImageScale>({ scaleX: 1, scaleY: 1 });

  useEffect(() => {
    if (!enabled) return;

    const updateScale = () => {
      if (imageRef.current && imageData) {
        const displayedWidth = imageRef.current.offsetWidth;
        const displayedHeight = imageRef.current.offsetHeight;
        const originalWidth = imageData.width || displayedWidth;
        const originalHeight = imageData.height || displayedHeight;
        
        setScale({
          scaleX: displayedWidth / originalWidth,
          scaleY: displayedHeight / originalHeight,
        });
      }
    };

    // Update scale when image loads or window resizes
    if (imageRef.current) {
      imageRef.current.addEventListener('load', updateScale);
      window.addEventListener('resize', updateScale);
      updateScale();
    }

    return () => {
      if (imageRef.current) {
        imageRef.current.removeEventListener('load', updateScale);
      }
      window.removeEventListener('resize', updateScale);
    };
  }, [imageRef, imageData, enabled]);

  return scale;
}

