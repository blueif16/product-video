/**
 * ScaleIn Animation Wrapper - ENHANCED
 * 
 * Supports custom bezier curves, continuous motion, and advanced transforms.
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

type Origin = "center" | "top" | "bottom" | "left" | "right" | "top-left" | "top-right" | "bottom-left" | "bottom-right";

interface ScaleInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  startScale?: number;
  endScale?: number;
  origin?: Origin;
  feel?: AnimationFeel;
  /** NEW: Custom spring config (overrides feel) */
  springConfig?: SpringConfig;
  /** NEW: Custom easing string (overrides spring) */
  easing?: string;
  /** NEW: Continuous motion after entrance */
  continuousMotion?: ContinuousMotionConfig;
  /** NEW: Include rotation */
  includeRotation?: boolean;
  startRotation?: number;
  style?: React.CSSProperties;
}

export const ScaleIn: React.FC<ScaleInProps> = ({
  children,
  delay = 0,
  duration,
  startScale = 0.85,
  endScale = 1,
  origin = "center",
  feel = "snappy",
  springConfig,
  easing,
  continuousMotion,
  includeRotation = false,
  startRotation = -5,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let progress: number;
  const effectiveFrame = frame - delay;
  
  if (easing) {
    const customEasing = getEasingFromString(easing);
    const linearProgress = duration 
      ? Math.min(1, Math.max(0, effectiveFrame / duration))
      : Math.min(1, Math.max(0, effectiveFrame / 20));
    progress = customEasing ? customEasing(linearProgress) : linearProgress;
  } else if (duration !== undefined) {
    progress = interpolate(
      frame,
      [delay, delay + duration],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else {
    const config = springConfig ?? SPRING_CONFIGS[feel];
    progress = spring({
      frame: effectiveFrame,
      fps,
      config,
    });
  }

  let scale = interpolate(progress, [0, 1], [startScale, endScale]);
  let rotation = includeRotation ? interpolate(progress, [0, 1], [startRotation, 0]) : 0;
  let opacity = progress;

  // Apply continuous motion after entrance
  if (continuousMotion && progress >= 1) {
    const entranceDuration = duration ?? 20;
    const motionFrame = effectiveFrame - entranceDuration;
    const motionValues = getContinuousMotionValues(motionFrame, continuousMotion);
    scale *= motionValues.scale;
    opacity *= motionValues.opacity;
  }

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
        transform: `scale(${scale}) rotate(${rotation}deg)`,
        transformOrigin: originMap[origin],
        opacity,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/**
 * PopIn - Bouncy scale animation (scale overshoots then settles)
 */
interface PopInProps {
  children: React.ReactNode;
  delay?: number;
  /** NEW: Custom spring config */
  springConfig?: SpringConfig;
  /** NEW: Continuous motion */
  continuousMotion?: ContinuousMotionConfig;
  style?: React.CSSProperties;
}

export const PopIn: React.FC<PopInProps> = ({
  children,
  delay = 0,
  springConfig,
  continuousMotion,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const config = springConfig ?? SPRING_CONFIGS.bouncy;
  const effectiveFrame = frame - delay;
  
  let scale = spring({
    frame: effectiveFrame,
    fps,
    config,
  });

  // Apply continuous motion
  if (continuousMotion && scale >= 0.99) {
    const motionFrame = Math.max(0, effectiveFrame - 20);
    const motionValues = getContinuousMotionValues(motionFrame, continuousMotion);
    scale *= motionValues.scale;
  }

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
 * ZoomIn - Smooth zoom without bounce
 */
interface ZoomInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  startScale?: number;
  feel?: AnimationFeel;
  /** NEW: Custom easing */
  easing?: string;
  /** NEW: Continuous motion */
  continuousMotion?: ContinuousMotionConfig;
  style?: React.CSSProperties;
}

export const ZoomIn: React.FC<ZoomInProps> = ({
  children,
  delay = 0,
  duration = 30,
  startScale = 0.8,
  feel = "smooth",
  easing,
  continuousMotion,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let progress: number;
  const effectiveFrame = frame - delay;
  
  if (easing) {
    const customEasing = getEasingFromString(easing);
    const linearProgress = Math.min(1, Math.max(0, effectiveFrame / duration));
    progress = customEasing ? customEasing(linearProgress) : linearProgress;
  } else if (duration !== undefined) {
    progress = interpolate(
      frame,
      [delay, delay + duration],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else {
    progress = spring({
      frame: effectiveFrame,
      fps,
      config: SPRING_CONFIGS[feel],
    });
  }

  let scale = interpolate(progress, [0, 1], [startScale, 1]);
  let opacity = interpolate(progress, [0, 0.5], [0, 1], { extrapolateRight: "clamp" });

  // Apply continuous motion
  if (continuousMotion && progress >= 1) {
    const motionFrame = effectiveFrame - duration;
    const motionValues = getContinuousMotionValues(motionFrame, continuousMotion);
    scale *= motionValues.scale;
    opacity *= motionValues.opacity;
  }

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

/**
 * ScaleOut - Scale down animation (for exits)
 */
interface ScaleOutProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  endScale?: number;
  feel?: AnimationFeel;
  easing?: string;
  style?: React.CSSProperties;
}

export const ScaleOut: React.FC<ScaleOutProps> = ({
  children,
  delay = 0,
  duration = 20,
  endScale = 0.85,
  feel = "snappy",
  easing,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let progress: number;
  const effectiveFrame = frame - delay;
  
  if (easing) {
    const customEasing = getEasingFromString(easing);
    const linearProgress = Math.min(1, Math.max(0, effectiveFrame / duration));
    progress = customEasing ? customEasing(linearProgress) : linearProgress;
  } else {
    progress = interpolate(
      frame,
      [delay, delay + duration],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  }

  const scale = interpolate(progress, [0, 1], [1, endScale]);
  const opacity = interpolate(progress, [0, 1], [1, 0]);

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

/**
 * PulseScale - Continuous pulsing scale animation
 */
interface PulseScaleProps {
  children: React.ReactNode;
  delay?: number;
  minScale?: number;
  maxScale?: number;
  cycleFrames?: number;
  style?: React.CSSProperties;
}

export const PulseScale: React.FC<PulseScaleProps> = ({
  children,
  delay = 0,
  minScale = 1.0,
  maxScale = 1.03,
  cycleFrames = 45,
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = Math.max(0, frame - delay);
  
  const phase = (effectiveFrame / cycleFrames) * Math.PI * 2;
  const progress = (Math.sin(phase) + 1) / 2;
  const scale = minScale + progress * (maxScale - minScale);

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
