/**
 * FadeIn Animation Wrapper
 * 
 * Fades children in with configurable delay, duration, and spring feel.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

type AnimationFeel = "snappy" | "smooth" | "bouncy";

// Spring physics presets
const SPRING_CONFIGS: Record<AnimationFeel, { damping: number; stiffness: number; mass: number }> = {
  snappy: { damping: 25, stiffness: 400, mass: 0.3 },
  smooth: { damping: 20, stiffness: 150, mass: 0.5 },
  bouncy: { damping: 8, stiffness: 200, mass: 0.5 },
};

interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;  // Duration in frames (uses linear if set, spring if not)
  feel?: AnimationFeel;  // Control spring physics when duration not set
  style?: React.CSSProperties;
}

export const FadeIn: React.FC<FadeInProps> = ({
  children,
  delay = 0,
  duration = 20,
  feel = "smooth",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  let opacity: number;
  
  if (duration !== undefined) {
    // Linear interpolation for precise timing
    opacity = interpolate(
      frame,
      [delay, delay + duration],
      [0, 1],
      { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
    );
  } else {
    // Spring animation with customizable feel
    opacity = spring({
      frame: frame - delay,
      fps,
      config: SPRING_CONFIGS[feel],
    });
  }

  return (
    <div style={{ opacity, ...style }}>
      {children}
    </div>
  );
};

/**
 * FadeInOut - Fades in then out at the end
 */
interface FadeInOutProps {
  children: React.ReactNode;
  delay?: number;
  fadeInDuration?: number;
  fadeOutDuration?: number;
  totalDuration: number;
  style?: React.CSSProperties;
}

export const FadeInOut: React.FC<FadeInOutProps> = ({
  children,
  delay = 0,
  fadeInDuration = 20,
  fadeOutDuration = 20,
  totalDuration,
  style,
}) => {
  const frame = useCurrentFrame();
  
  const fadeOutStart = totalDuration - fadeOutDuration;
  
  const opacity = interpolate(
    frame,
    [delay, delay + fadeInDuration, fadeOutStart, totalDuration],
    [0, 1, 1, 0],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );

  return (
    <div style={{ opacity, ...style }}>
      {children}
    </div>
  );
};
