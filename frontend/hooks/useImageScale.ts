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

    let mounted = true;
    let currentImage: HTMLImageElement | null = null;
    let rafId: number | null = null;
    let observer: ResizeObserver | null = null;

    const updateScale = () => {
      if (!currentImage || !mounted) return;
      const displayedWidth = currentImage.offsetWidth;
      const displayedHeight = currentImage.offsetHeight;
      const originalWidth = currentImage.naturalWidth || displayedWidth;
      const originalHeight = currentImage.naturalHeight || displayedHeight;

      if (!originalWidth || !originalHeight) return;
      setScale({
        scaleX: displayedWidth / originalWidth,
        scaleY: displayedHeight / originalHeight,
      });
    };

    const attachWhenReady = () => {
      if (!mounted) return;
      const el = imageRef.current;
      if (!el) {
        rafId = window.requestAnimationFrame(attachWhenReady);
        return;
      }

      currentImage = el;
      currentImage.addEventListener('load', updateScale);
      window.addEventListener('resize', updateScale);
      observer = new ResizeObserver(updateScale);
      observer.observe(currentImage);
      updateScale();
    };

    attachWhenReady();

    return () => {
      mounted = false;
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
      }
      if (currentImage) {
        currentImage.removeEventListener('load', updateScale);
      }
      window.removeEventListener('resize', updateScale);
      if (observer) {
        observer.disconnect();
      }
    };
  }, [enabled, imageRef]);

  return scale;
}
