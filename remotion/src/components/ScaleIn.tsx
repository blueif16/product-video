/**
 * ScaleIn Animation Wrapper
 * 
 * Scales children in with spring physics and configurable origin.
 * Supports animation "feel": snappy, smooth, bouncy
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

type Origin = "center" | "top" | "bottom" | "left" | "right" | "top-left" | "top-right" | "bottom-left" | "bottom-right";
type AnimationFeel = "snappy" | "smooth" | "bouncy";

// Spring physics presets
const SPRING_CONFIGS: Record<AnimationFeel, { damping: number; stiffness: number; mass: number }> = {
  snappy: { damping: 25, stiffness: 400, mass: 0.3 },
  smooth: { damping: 20, stiffness: 150, mass: 0.5 },
  bouncy: { damping: 8, stiffness: 200, mass: 0.5 },
};

interface ScaleInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;  // Duration in frames (uses linear if set, spring if not)
  startScale?: number;
  endScale?: number;
  origin?: Origin;
  feel?: AnimationFeel;  // NEW: Control spring physics
  style?: React.CSSProperties;
}

export const ScaleIn: React.FC<ScaleInProps> = ({
  children,
  delay = 0,
  duration,
  startScale = 0.85,  // Start close to 1 for punchy feel
  endScale = 1,
  origin = "center",
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

  const scale = interpolate(progress, [0, 1], [startScale, endScale]);

  const originMap: Record<Origin, string> = {
    center: "center center",
    top: "center top",
    bottom: "center bottom",
    left: "left center",
    right: "right center",
    "top-left": "left top",
    "top-right": "right top",
    "bottom-left": "left bottom",
    "bottom-right": "right bottom",
  };

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        transformOrigin: originMap[origin],
        opacity: progress,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/**
 * PopIn - Bouncy scale animation (scale overshoots then settles)
 * Always uses bouncy spring physics for playful feel
 */
interface PopInProps {
  children: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
}

export const PopIn: React.FC<PopInProps> = ({
  children,
  delay = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Always bouncy for PopIn
  const scale = spring({
    frame: frame - delay,
    fps,
    config: SPRING_CONFIGS.bouncy,
  });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        transformOrigin: "center center",
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/**
 * ZoomIn - Smooth zoom without bounce (uses smooth feel)
 */
interface ZoomInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  startScale?: number;
  feel?: AnimationFeel;
  style?: React.CSSProperties;
}

export const ZoomIn: React.FC<ZoomInProps> = ({
  children,
  delay = 0,
  duration = 30,
  startScale = 0.8,
  feel = "smooth",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let progress: number;
  
  if (duration !== undefined) {
    progress = interpolate(
      frame,
      [delay, delay + duration],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else {
    progress = spring({
      frame: frame - delay,
      fps,
      config: SPRING_CONFIGS[feel],
    });
  }

  const scale = interpolate(progress, [0, 1], [startScale, 1]);
  const opacity = interpolate(progress, [0, 0.5], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        transformOrigin: "center center",
        opacity,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
