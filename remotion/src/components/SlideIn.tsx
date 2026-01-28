/**
 * SlideIn Animation Wrapper - ENHANCED
 * 
 * Supports custom bezier curves, irregular stagger, and continuous motion.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { 
  SPRING_CONFIGS, 
  AnimationFeel, 
  SpringConfig,
  getEasingFromString,
  getContinuousMotionValues,
  ContinuousMotionConfig,
} from "../lib/easing";

type Direction = "left" | "right" | "top" | "bottom";

interface SlideInProps {
  children: React.ReactNode;
  direction?: Direction;
  delay?: number;
  duration?: number;
  distance?: number;
  feel?: AnimationFeel;
  /** NEW: Custom spring config (overrides feel) */
  springConfig?: SpringConfig;
  /** NEW: Custom easing string (overrides spring) */
  easing?: string;
  /** NEW: Continuous motion after entrance */
  continuousMotion?: ContinuousMotionConfig;
  /** NEW: Include scale in animation */
  includeScale?: boolean;
  startScale?: number;
  style?: React.CSSProperties;
}

export const SlideIn: React.FC<SlideInProps> = ({
  children,
  direction = "left",
  delay = 0,
  duration,
  distance = 50,
  feel = "snappy",
  springConfig,
  easing,
  continuousMotion,
  includeScale = false,
  startScale = 0.95,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let progress: number;
  const effectiveFrame = frame - delay;
  
  if (easing) {
    // Custom bezier easing
    const customEasing = getEasingFromString(easing);
    const linearProgress = duration 
      ? Math.min(1, Math.max(0, effectiveFrame / duration))
      : Math.min(1, Math.max(0, effectiveFrame / 20));
    progress = customEasing ? customEasing(linearProgress) : linearProgress;
  } else if (duration !== undefined) {
    // Linear interpolation for precise timing
    progress = interpolate(
      frame,
      [delay, delay + duration],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else {
    // Spring animation with customizable feel
    const config = springConfig ?? SPRING_CONFIGS[feel];
    progress = spring({
      frame: effectiveFrame,
      fps,
      config,
    });
  }

  const getBaseOffset = (): number => {
    return interpolate(progress, [0, 1], [distance, 0]);
  };

  let translateX = 0;
  let translateY = 0;
  const offset = getBaseOffset();
  
  switch (direction) {
    case "left":
      translateX = -offset;
      break;
    case "right":
      translateX = offset;
      break;
    case "top":
      translateY = -offset;
      break;
    case "bottom":
      translateY = offset;
      break;
  }

  let scale = includeScale ? interpolate(progress, [0, 1], [startScale, 1]) : 1;
  let opacity = progress;

  // Apply continuous motion after entrance
  if (continuousMotion && progress >= 1) {
    const entranceDuration = duration ?? 20;
    const motionFrame = effectiveFrame - entranceDuration;
    const motionValues = getContinuousMotionValues(motionFrame, continuousMotion);
    translateX += motionValues.x;
    translateY += motionValues.y;
    scale *= motionValues.scale;
    opacity *= motionValues.opacity;
  }

  return (
    <div
      style={{
        transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
        opacity,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/**
 * SlideUp - Convenience component for upward slide
 */
export const SlideUp: React.FC<Omit<SlideInProps, "direction">> = (props) => (
  <SlideIn {...props} direction="bottom" />
);

/**
 * SlideDown - Convenience component for downward slide
 */
export const SlideDown: React.FC<Omit<SlideInProps, "direction">> = (props) => (
  <SlideIn {...props} direction="top" />
);

/**
 * SlideLeft - Convenience component for leftward slide
 */
export const SlideLeft: React.FC<Omit<SlideInProps, "direction">> = (props) => (
  <SlideIn {...props} direction="right" />
);

/**
 * SlideRight - Convenience component for rightward slide
 */
export const SlideRight: React.FC<Omit<SlideInProps, "direction">> = (props) => (
  <SlideIn {...props} direction="left" />
);
