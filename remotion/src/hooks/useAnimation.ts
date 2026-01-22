/**
 * Animation Hooks
 * 
 * Custom hooks for common animation patterns.
 */

import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

/**
 * useProgress - Returns normalized progress (0-1) for current sequence
 */
export const useProgress = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return frame / durationInFrames;
};

/**
 * useFadeIn - Returns opacity value for fade in animation
 */
export const useFadeIn = (delay = 0, duration = 20) => {
  const frame = useCurrentFrame();
  return interpolate(
    frame,
    [delay, delay + duration],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
};

/**
 * useFadeOut - Returns opacity value for fade out at end
 */
export const useFadeOut = (duration = 20) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const fadeStart = durationInFrames - duration;
  
  return interpolate(
    frame,
    [fadeStart, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
};

/**
 * useFadeInOut - Combined fade in at start, fade out at end
 */
export const useFadeInOut = (fadeInDuration = 20, fadeOutDuration = 20) => {
  const fadeIn = useFadeIn(0, fadeInDuration);
  const fadeOut = useFadeOut(fadeOutDuration);
  return Math.min(fadeIn, fadeOut);
};

/**
 * useSpring - Simplified spring animation hook
 */
export const useSpring = (
  delay = 0,
  config?: { damping?: number; stiffness?: number; mass?: number }
) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  return spring({
    frame: frame - delay,
    fps,
    config: {
      damping: config?.damping ?? 200,
      stiffness: config?.stiffness ?? 100,
      mass: config?.mass ?? 1,
    },
  });
};

/**
 * useSlide - Returns transform value for slide animation
 */
export const useSlide = (
  direction: "left" | "right" | "up" | "down",
  delay = 0,
  distance = 100
) => {
  const progress = useSpring(delay);
  const offset = interpolate(progress, [0, 1], [distance, 0]);
  
  const transforms: Record<string, string> = {
    left: `translateX(${-offset}px)`,
    right: `translateX(${offset}px)`,
    up: `translateY(${-offset}px)`,
    down: `translateY(${offset}px)`,
  };
  
  return {
    transform: transforms[direction],
    opacity: progress,
  };
};

/**
 * useScale - Returns scale value with spring animation
 */
export const useScale = (delay = 0, from = 0, to = 1) => {
  const progress = useSpring(delay, { damping: 12 });
  return interpolate(progress, [0, 1], [from, to]);
};

/**
 * useRotate - Returns rotation value
 */
export const useRotate = (
  delay = 0,
  fromDeg = -10,
  toDeg = 0
) => {
  const progress = useSpring(delay);
  const rotation = interpolate(progress, [0, 1], [fromDeg, toDeg]);
  return `rotate(${rotation}deg)`;
};

/**
 * usePulse - Returns oscillating value for pulsing effects
 */
export const usePulse = (speed = 20, intensity = 0.05) => {
  const frame = useCurrentFrame();
  return 1 + Math.sin(frame / speed) * intensity;
};

/**
 * useStagger - Returns delay value for staggered animations
 */
export const useStagger = (index: number, staggerAmount = 5) => {
  return index * staggerAmount;
};

/**
 * useEnterExit - Combined enter and exit animation
 */
export const useEnterExit = (
  enterDuration = 20,
  exitDuration = 20
) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const enter = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  const exit = spring({
    frame: frame - (durationInFrames - exitDuration),
    fps,
    config: { damping: 200 },
  });

  // Combine: enter drives 0→1, exit drives 1→0
  return Math.min(enter, 1 - Math.max(0, exit));
};

/**
 * useTypewriter - Returns visible character count for typewriter effect
 */
export const useTypewriter = (
  textLength: number,
  speed = 2,
  delay = 0
) => {
  const frame = useCurrentFrame();
  const effectiveFrame = Math.max(0, frame - delay);
  return Math.min(Math.floor(effectiveFrame / speed), textLength);
};

/**
 * useCountUp - Returns animated number for count-up effect
 */
export const useCountUp = (
  from: number,
  to: number,
  delay = 0,
  duration = 60
) => {
  const frame = useCurrentFrame();
  return interpolate(
    frame,
    [delay, delay + duration],
    [from, to],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
};

/**
 * useParallax - Returns offset value for parallax effects
 */
export const useParallax = (speed = 0.5, maxOffset = 50) => {
  const progress = useProgress();
  return progress * maxOffset * speed;
};
