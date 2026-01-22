/**
 * SlideIn Animation Wrapper
 * 
 * Slides children in from specified direction with customizable spring physics.
 * Supports animation "feel": snappy, smooth, bouncy
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

type Direction = "left" | "right" | "top" | "bottom";
type AnimationFeel = "snappy" | "smooth" | "bouncy";

// Spring physics presets
const SPRING_CONFIGS: Record<AnimationFeel, { damping: number; stiffness: number; mass: number }> = {
  snappy: { damping: 25, stiffness: 400, mass: 0.3 },
  smooth: { damping: 20, stiffness: 150, mass: 0.5 },
  bouncy: { damping: 8, stiffness: 200, mass: 0.5 },
};

interface SlideInProps {
  children: React.ReactNode;
  direction?: Direction;
  delay?: number;
  duration?: number;  // Duration in frames (uses linear if set, spring if not)
  distance?: number;
  feel?: AnimationFeel;  // NEW: Control spring physics
  style?: React.CSSProperties;
}

export const SlideIn: React.FC<SlideInProps> = ({
  children,
  direction = "left",
  delay = 0,
  duration,
  distance = 50,
  feel = "snappy",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let progress: number;
  
  if (duration !== undefined) {
    // Linear interpolation for precise timing
    progress = interpolate(
      frame,
      [delay, delay + duration],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else {
    // Spring animation with customizable feel
    const springConfig = SPRING_CONFIGS[feel];
    progress = spring({
      frame: frame - delay,
      fps,
      config: springConfig,
    });
  }

  const getTransform = (): string => {
    const offset = interpolate(progress, [0, 1], [distance, 0]);
    
    switch (direction) {
      case "left":
        return `translateX(${-offset}px)`;
      case "right":
        return `translateX(${offset}px)`;
      case "top":
        return `translateY(${-offset}px)`;
      case "bottom":
        return `translateY(${offset}px)`;
      default:
        return "none";
    }
  };

  return (
    <div
      style={{
        transform: getTransform(),
        opacity: progress,
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
