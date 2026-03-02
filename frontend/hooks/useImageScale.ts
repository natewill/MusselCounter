import { useState, useEffect } from 'react';

interface ImageScale {
  scaleX: number;
  scaleY: number;
}

interface UseImageScaleProps {
  imageRef: React.RefObject<HTMLImageElement>;
  enabled?: boolean;
}

export function useImageScale({ imageRef, enabled = true }: UseImageScaleProps): ImageScale {
  const [scale, setScale] = useState<ImageScale>({ scaleX: 1, scaleY: 1 });

  useEffect(() => {
    if (!enabled) return;
    const currentImage = imageRef.current;

    const updateScale = () => {
      if (currentImage) {
        const displayedWidth = currentImage.offsetWidth;
        const displayedHeight = currentImage.offsetHeight;
        const originalWidth = currentImage.naturalWidth || displayedWidth;
        const originalHeight = currentImage.naturalHeight || displayedHeight;
        
        setScale({
          scaleX: displayedWidth / originalWidth,
          scaleY: displayedHeight / originalHeight,
        });
      }
    };

    // Update scale when image loads or window resizes
    if (currentImage) {
      currentImage.addEventListener('load', updateScale);
      window.addEventListener('resize', updateScale);
      updateScale();
    }

    return () => {
      if (currentImage) {
        currentImage.removeEventListener('load', updateScale);
      }
      window.removeEventListener('resize', updateScale);
    };
  }, [imageRef, enabled]);

  return scale;
}
