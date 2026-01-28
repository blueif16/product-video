/**
 * Advanced Easing System
 * 
 * Comprehensive easing utilities including bezier curves, spring physics,
 * and preset configurations for high-quality animations.
 */

import { Easing } from "remotion";

// ─────────────────────────────────────────────────────────────
// SPRING PHYSICS PRESETS
// ─────────────────────────────────────────────────────────────

export interface SpringConfig {
  damping: number;
  stiffness: number;
  mass: number;
}

export const SPRING_CONFIGS = {
  // Original presets
  snappy: { damping: 25, stiffness: 400, mass: 0.3 },
  smooth: { damping: 20, stiffness: 150, mass: 0.5 },
  bouncy: { damping: 8, stiffness: 200, mass: 0.5 },
  
  // NEW: Advanced presets from RAG knowledge
  kinetic: { damping: 12, stiffness: 300, mass: 0.4 },      // Energetic with slight overshoot
  elegant: { damping: 18, stiffness: 100, mass: 0.6 },      // Luxurious, no overshoot
  anticipate: { damping: 10, stiffness: 250, mass: 0.5 },   // Anticipation + overshoot
  gentle: { damping: 15, stiffness: 80, mass: 0.8 },        // Very soft landing
  sharp: { damping: 30, stiffness: 500, mass: 0.2 },        // Instant snap
  wobbly: { damping: 5, stiffness: 180, mass: 0.6 },        // Playful wobble
} as const;

export type AnimationFeel = keyof typeof SPRING_CONFIGS;

// ─────────────────────────────────────────────────────────────
// BEZIER CURVE PRESETS
// ─────────────────────────────────────────────────────────────

export const BEZIER_PRESETS = {
  // Standard easing
  linear: [0, 0, 1, 1],
  ease: [0.25, 0.1, 0.25, 1.0],
  easeIn: [0.42, 0, 1.0, 1.0],
  easeOut: [0, 0, 0.58, 1.0],
  easeInOut: [0.42, 0, 0.58, 1.0],
  
  // NEW: Advanced easing from RAG knowledge
  kineticOvershoot: [0.34, 1.56, 0.64, 1],         // Energetic with overshoot
  elegantSmooth: [0.25, 0.1, 0.25, 1.0],           // Luxurious, no overshoot
  boldAnticipate: [0.68, -0.55, 0.265, 1.55],      // Anticipation + overshoot
  sharpSnap: [0.7, 0, 0.84, 0],                    // Quick snap, no ease out
  slowStart: [0.6, 0, 0.4, 1],                     // Slow start, fast end
  slowEnd: [0.4, 0, 0.6, 1],                       // Fast start, slow end
  bounce: [0.34, 1.4, 0.64, 1],                    // Subtle bounce
  elastic: [0.5, 1.8, 0.5, 0.8],                   // Elastic overshoot
  emphasize: [0.2, 0, 0, 1],                       // Strong deceleration
} as const;

export type BezierPreset = keyof typeof BEZIER_PRESETS;

// ─────────────────────────────────────────────────────────────
// BEZIER PARSING UTILITIES
// ─────────────────────────────────────────────────────────────

/**
 * Parse a CSS cubic-bezier string to an array of 4 numbers
 * @param bezierString - e.g., "cubic-bezier(0.34, 1.56, 0.64, 1)"
 * @returns [x1, y1, x2, y2] or null if invalid
 */
export function parseBezierString(bezierString: string): [number, number, number, number] | null {
  // Check if it's a preset name
  if (bezierString in BEZIER_PRESETS) {
    return BEZIER_PRESETS[bezierString as BezierPreset] as [number, number, number, number];
  }
  
  // Parse cubic-bezier(x1, y1, x2, y2) format
  const match = bezierString.match(/cubic-bezier\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)/);
  if (match) {
    const values = match.slice(1, 5).map(parseFloat);
    if (values.every(v => !isNaN(v))) {
      return values as [number, number, number, number];
    }
  }
  
  // Parse simple array format: "0.34, 1.56, 0.64, 1"
  const simpleMatch = bezierString.split(',').map(s => parseFloat(s.trim()));
  if (simpleMatch.length === 4 && simpleMatch.every(v => !isNaN(v))) {
    return simpleMatch as [number, number, number, number];
  }
  
  return null;
}

/**
 * Create a Remotion easing function from bezier values
 */
export function createBezierEasing(bezier: [number, number, number, number]): (t: number) => number {
  return Easing.bezier(bezier[0], bezier[1], bezier[2], bezier[3]);
}

/**
 * Get easing function from string (preset name or cubic-bezier)
 */
export function getEasingFromString(easingString: string): ((t: number) => number) | null {
  const bezierValues = parseBezierString(easingString);
  if (bezierValues) {
    return createBezierEasing(bezierValues);
  }
  return null;
}

// ─────────────────────────────────────────────────────────────
// CONTINUOUS MOTION CONFIGURATIONS
// ─────────────────────────────────────────────────────────────

export interface ContinuousMotionConfig {
  type: "oscillate" | "pulse" | "drift" | "breathe" | "float";
  intensity?: number;      // 0-1 scale
  speed?: number;          // Frames per cycle
  axis?: "x" | "y" | "both";
}

export const CONTINUOUS_MOTION_PRESETS: Record<string, ContinuousMotionConfig> = {
  gentleFloat: { type: "float", intensity: 0.3, speed: 120, axis: "y" },
  subtlePulse: { type: "pulse", intensity: 0.2, speed: 45 },
  slowDrift: { type: "drift", intensity: 0.4, speed: 90, axis: "both" },
  breathe: { type: "breathe", intensity: 0.15, speed: 60 },
  microOscillate: { type: "oscillate", intensity: 0.1, speed: 30, axis: "y" },
};

/**
 * Calculate continuous motion offset for a given frame
 */
export function getContinuousMotionValues(
  frame: number,
  config: ContinuousMotionConfig
): { x: number; y: number; scale: number; opacity: number } {
  const intensity = config.intensity ?? 0.3;
  const speed = config.speed ?? 60;
  const phase = (frame / speed) * Math.PI * 2;
  
  let x = 0, y = 0, scale = 1, opacity = 1;
  
  switch (config.type) {
    case "oscillate":
      if (config.axis === "x" || config.axis === "both") {
        x = Math.sin(phase) * 3 * intensity;
      }
      if (config.axis === "y" || config.axis === "both" || !config.axis) {
        y = Math.sin(phase) * 3 * intensity;
      }
      break;
      
    case "pulse":
      scale = 1 + Math.sin(phase) * 0.03 * intensity;
      break;
      
    case "drift":
      x = Math.sin(phase * 0.7) * 5 * intensity;
      y = Math.cos(phase * 0.5) * 3 * intensity;
      break;
      
    case "breathe":
      scale = 1 + Math.sin(phase) * 0.02 * intensity;
      opacity = 1 - Math.sin(phase) * 0.1 * intensity;
      break;
      
    case "float":
      y = Math.sin(phase) * 5 * intensity;
      x = Math.sin(phase * 0.5) * 2 * intensity;
      break;
  }
  
  return { x, y, scale, opacity };
}

// ─────────────────────────────────────────────────────────────
// STAGGER UTILITIES
// ─────────────────────────────────────────────────────────────

/**
 * Get stagger delay for an item at given index
 * Supports both uniform delays and irregular arrays
 */
export function getStaggerDelay(
  index: number,
  staggerDelay: number | number[],
  durationVariance?: number
): number {
  let baseDelay: number;
  
  if (Array.isArray(staggerDelay)) {
    // Irregular stagger: cycle through array
    baseDelay = staggerDelay[index % staggerDelay.length];
    // For items beyond array length, accumulate
    const fullCycles = Math.floor(index / staggerDelay.length);
    const sumOfArray = staggerDelay.reduce((a, b) => a + b, 0);
    baseDelay = fullCycles * sumOfArray + 
      staggerDelay.slice(0, index % staggerDelay.length).reduce((a, b) => a + b, 0) +
      staggerDelay[index % staggerDelay.length];
  } else {
    baseDelay = index * staggerDelay;
  }
  
  // Add variance for organic feel
  if (durationVariance && durationVariance > 0) {
    const variance = (Math.sin(index * 7.13) * 0.5 + 0.5) * durationVariance * 2 - durationVariance;
    baseDelay += variance;
  }
  
  return Math.max(0, baseDelay);
}

/**
 * Get duration with variance for organic animations
 */
export function getDurationWithVariance(
  baseDuration: number,
  index: number,
  variance?: number
): number {
  if (!variance || variance <= 0) return baseDuration;
  
  // Deterministic pseudo-random based on index
  const variation = (Math.sin(index * 13.37) * 0.5 + 0.5) * variance * 2 - variance;
  return Math.max(1, baseDuration + variation);
}

// ─────────────────────────────────────────────────────────────
// TIMING UTILITIES
// ─────────────────────────────────────────────────────────────

/**
 * Convert milliseconds to frames
 */
export function msToFrames(ms: number, fps: number): number {
  return Math.round((ms / 1000) * fps);
}

/**
 * Convert frames to milliseconds
 */
export function framesToMs(frames: number, fps: number): number {
  return (frames / fps) * 1000;
}

/**
 * Get default exit duration (20% shorter than entrance)
 */
export function getDefaultExitDuration(enterDuration: number): number {
  return Math.round(enterDuration * 0.8);
}

// ─────────────────────────────────────────────────────────────
// SHADOW UTILITIES
// ─────────────────────────────────────────────────────────────

export interface ShadowLayer {
  offsetX?: number;
  offsetY?: number;
  blur: number;
  spread?: number;
  color?: string;
  opacity: number;
}

/**
 * Generate multi-layer shadow CSS string
 */
export function generateMultiLayerShadow(
  layers: ShadowLayer[],
  baseColor: string = "rgba(0, 0, 0, 1)"
): string {
  return layers
    .map(layer => {
      const color = layer.color || baseColor;
      // Extract RGB and apply layer opacity
      const rgba = color.startsWith("rgba") 
        ? color.replace(/[\d.]+\)$/, `${layer.opacity})`)
        : `rgba(0, 0, 0, ${layer.opacity})`;
      
      return `${layer.offsetX ?? 0}px ${layer.offsetY ?? 0}px ${layer.blur}px ${layer.spread ?? 0}px ${rgba}`;
    })
    .join(", ");
}

/**
 * Preset multi-layer shadows from RAG knowledge
 */
export const SHADOW_PRESETS = {
  depth: [
    { blur: 10, opacity: 0.1 },
    { blur: 40, opacity: 0.15 },
    { blur: 80, opacity: 0.08 },
  ],
  floating: [
    { offsetY: 4, blur: 6, opacity: 0.1 },
    { offsetY: 10, blur: 20, opacity: 0.1 },
    { offsetY: 20, blur: 40, opacity: 0.05 },
  ],
  dramatic: [
    { blur: 20, opacity: 0.2 },
    { blur: 60, opacity: 0.15 },
    { blur: 120, opacity: 0.1 },
  ],
  soft: [
    { blur: 8, opacity: 0.05 },
    { blur: 24, opacity: 0.08 },
  ],
};
