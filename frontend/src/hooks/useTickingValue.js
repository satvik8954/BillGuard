import { useEffect, useRef, useState } from "react";

const REDUCED_MOTION = typeof window !== "undefined" && window.matchMedia
  ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
  : false;

/**
 * Animates a number climbing upward in real time, framerate-independent.
 * Used to dramatize "the meter is still running" — the per-second rate is
 * intentionally accelerated for visual effect (it's a hero animation, not
 * a live billing readout), but it never runs when the visitor has asked
 * for reduced motion.
 */
export function useTickingValue(start, perSecond) {
  const [value, setValue] = useState(start);
  const startTimeRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    if (REDUCED_MOTION) {
      setValue(start);
      return;
    }

    function tick(now) {
      if (startTimeRef.current === null) startTimeRef.current = now;
      const elapsedSeconds = (now - startTimeRef.current) / 1000;
      setValue(start + elapsedSeconds * perSecond);
      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [start, perSecond]);

  return value;
}
