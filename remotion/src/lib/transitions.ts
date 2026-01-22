/**
 * Transition Presets
 * 
 * Pre-configured transition timings and presentations
 * for consistent scene-to-scene animations.
 */

import { linearTiming, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";

/**
 * Quick fade - for fast cuts
 */
export const quickFade = {
  timing: linearTiming({ durationInFrames: 10 }),
  presentation: fade(),
};

/**
 * Standard fade - default transition
 */
export const standardFade = {
  timing: linearTiming({ durationInFrames: 20 }),
  presentation: fade(),
};

/**
 * Slow fade - cinematic dissolve
 */
export const slowFade = {
  timing: linearTiming({ durationInFrames: 45 }),
  presentation: fade(),
};

/**
 * Spring fade - bouncy, energetic
 */
export const springFade = {
  timing: springTiming({
    config: { damping: 200, stiffness: 100 },
    durationInFrames: 30,
  }),
  presentation: fade(),
};

/**
 * Slide left - content enters from right
 */
export const slideLeft = {
  timing: springTiming({
    config: { damping: 200 },
    durationInFrames: 25,
  }),
  presentation: slide({ direction: "from-right" }),
};

/**
 * Slide right - content enters from left
 */
export const slideRight = {
  timing: springTiming({
    config: { damping: 200 },
    durationInFrames: 25,
  }),
  presentation: slide({ direction: "from-left" }),
};

/**
 * Slide up - content enters from bottom
 */
export const slideUp = {
  timing: springTiming({
    config: { damping: 200 },
    durationInFrames: 25,
  }),
  presentation: slide({ direction: "from-bottom" }),
};

/**
 * Slide down - content enters from top
 */
export const slideDown = {
  timing: springTiming({
    config: { damping: 200 },
    durationInFrames: 25,
  }),
  presentation: slide({ direction: "from-top" }),
};

/**
 * Wipe right - horizontal wipe
 */
export const wipeRight = {
  timing: linearTiming({ durationInFrames: 20 }),
  presentation: wipe({ direction: "from-left" }),
};

/**
 * Wipe left
 */
export const wipeLeft = {
  timing: linearTiming({ durationInFrames: 20 }),
  presentation: wipe({ direction: "from-right" }),
};

/**
 * Get transition preset by name
 */
export const getTransition = (name: string) => {
  const transitions: Record<string, typeof quickFade> = {
    quickFade,
    standardFade,
    slowFade,
    springFade,
    slideLeft,
    slideRight,
    slideUp,
    slideDown,
    wipeRight,
    wipeLeft,
  };
  
  return transitions[name] || standardFade;
};

/**
 * Transition type for schemas
 */
export type TransitionName = 
  | "quickFade" 
  | "standardFade" 
  | "slowFade" 
  | "springFade"
  | "slideLeft" 
  | "slideRight" 
  | "slideUp" 
  | "slideDown"
  | "wipeRight" 
  | "wipeLeft";
