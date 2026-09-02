import { useEffect, useState } from 'react';

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  return reduced;
}

export function useStoryProgress(trackRef, reducedMotion) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return undefined;

    let frame = 0;
    let current = 0;
    let target = 0;

    const read = () => {
      const total = track.offsetHeight - window.innerHeight;
      if (total <= 0) return 0;
      return Math.min(1, Math.max(0, -track.getBoundingClientRect().top / total));
    };

    const tick = () => {
      target = read();
      if (reducedMotion) {
        current = target;
      } else {
        current += (target - current) * 0.08;
        if (Math.abs(target - current) < 0.0005) current = target;
      }
      setProgress(current);
      if (Math.abs(target - current) > 0.0005) {
        frame = requestAnimationFrame(tick);
      } else {
        frame = 0;
      }
    };

    const kick = () => {
      if (!frame) frame = requestAnimationFrame(tick);
    };

    kick();
    window.addEventListener('scroll', kick, { passive: true });
    window.addEventListener('resize', kick);
    return () => {
      window.removeEventListener('scroll', kick);
      window.removeEventListener('resize', kick);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [trackRef, reducedMotion]);

  return progress;
}

export function fade(progress, enter, full, hold, leave) {
  if (progress < enter) return 0;
  if (progress < full) return (progress - enter) / (full - enter || 1);
  if (progress < hold) return 1;
  if (progress < leave) return 1 - (progress - hold) / (leave - hold || 1);
  return 0;
}

export function layerStyle(opacity, translateY = 18, scale = 1) {
  const shown = opacity > 0.012;
  return {
    opacity,
    transform: `translate3d(0, ${(1 - opacity) * translateY}px, 0) scale(${scale})`,
    visibility: shown ? 'visible' : 'hidden',
    pointerEvents: opacity > 0.45 ? 'auto' : 'none',
  };
}
