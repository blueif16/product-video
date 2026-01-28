/**
 * FadeIn Animation Wrapper - ENHANCED
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

interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  feel?: AnimationFeel;
  /** NEW: Custom spring config (overrides feel) */
  springConfig?: SpringConfig;
  /** NEW: Custom easing string (overrides spring) */
  easing?: string;
  /** NEW: Continuous motion after entrance */
  continuousMotion?: ContinuousMotionConfig;
  /** NEW: Include slight scale in fade */
  includeScale?: boolean;
  startScale?: number;
  /** NEW: Include blur effect */
  includeBlur?: boolean;
  startBlur?: number;
  style?: React.CSSProperties;
}

export const FadeIn: React.FC<FadeInProps> = ({
  children,
  delay = 0,
  duration = 20,
  feel = "smooth",
  springConfig,
  easing,
  continuousMotion,
  includeScale = false,
  startScale = 0.98,
  includeBlur = false,
  startBlur = 10,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  let opacity: number;
  const effectiveFrame = frame - delay;
  
  if (easing) {
    const customEasing = getEasingFromString(easing);
    const linearProgress = Math.min(1, Math.max(0, effectiveFrame / duration));
    opacity = customEasing ? customEasing(linearProgress) : linearProgress;
  } else if (duration !== undefined) {
    opacity = interpolate(
      frame,
      [delay, delay + duration],
      [0, 1],
      { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
    );
  } else {
    const config = springConfig ?? SPRING_CONFIGS[feel];
    opacity = spring({
      frame: effectiveFrame,
      fps,
      config,
    });
  }

  let scale = includeScale ? interpolate(opacity, [0, 1], [startScale, 1]) : 1;
  let blur = includeBlur ? interpolate(opacity, [0, 1], [startBlur, 0]) : 0;

  // Apply continuous motion after entrance
  if (continuousMotion && opacity >= 1) {
    const entranceDuration = duration ?? 20;
    const motionFrame = effectiveFrame - entranceDuration;
    const motionValues = getContinuousMotionValues(motionFrame, continuousMotion);
    scale *= motionValues.scale;
    opacity *= motionValues.opacity;
  }

  return (
    <div
      style={{
        opacity,
        transform: includeScale ? `scale(${scale})` : undefined,
        filter: includeBlur ? `blur(${blur}px)` : undefined,
        ...style,
      }}
    >
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
  /** NEW: Custom easing */
  easing?: string;
  /** NEW: Hold at full opacity ratio (0-1, where 0.8 means 80% of middle is full opacity) */
  holdRatio?: number;
  style?: React.CSSProperties;
}

export const FadeInOut: React.FC<FadeInOutProps> = ({
  children,
  delay = 0,
  fadeInDuration = 20,
  fadeOutDuration = 20,
  totalDuration,
  easing,
  holdRatio,
  style,
}) => {
  const frame = useCurrentFrame();
  const customEasing = easing ? getEasingFromString(easing) : null;
  
  let fadeOutStart: number;
  
  if (holdRatio !== undefined) {
    // Calculate fade times based on hold ratio
    const holdDuration = totalDuration * holdRatio;
    const fadeDuration = (totalDuration - holdDuration) / 2;
    fadeOutStart = delay + fadeDuration + holdDuration;
  } else {
    fadeOutStart = totalDuration - fadeOutDuration;
  }
  
  let opacity = interpolate(
    frame,
    [delay, delay + fadeInDuration, fadeOutStart, totalDuration],
    [0, 1, 1, 0],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );
  
  // Apply custom easing to the in/out portions
  if (customEasing) {
    if (frame < delay + fadeInDuration) {
      const inProgress = Math.max(0, (frame - delay) / fadeInDuration);
      opacity = customEasing(inProgress);
    } else if (frame > fadeOutStart) {
      const outProgress = Math.min(1, (frame - fadeOutStart) / (totalDuration - fadeOutStart));
      opacity = 1 - customEasing(outProgress);
    }
  }

  return (
    <div style={{ opacity, ...style }}>
      {children}
    </div>
  );
};

/**
 * FadeOut - Fade out animation (for exits)
 */
interface FadeOutProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  /** NEW: Custom easing */
  easing?: string;
  /** NEW: Include scale out */
  includeScale?: boolean;
  endScale?: number;
  style?: React.CSSProperties;
}

export const FadeOut: React.FC<FadeOutProps> = ({
  children,
  delay = 0,
  duration = 20,
  easing,
  includeScale = false,
  endScale = 0.95,
  style,
}) => {
  const frame = useCurrentFrame();
  const customEasing = easing ? getEasingFromString(easing) : null;
  
  let progress = interpolate(
    frame,
    [delay, delay + duration],
    [0, 1],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );
  
  if (customEasing) {
    progress = customEasing(progress);
  }

  const opacity = 1 - progress;
  const scale = includeScale ? interpolate(progress, [0, 1], [1, endScale]) : 1;

  return (
    <div
      style={{
        opacity,
        transform: includeScale ? `scale(${scale})` : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/**
 * CrossFade - Fade between two elements
 */
interface CrossFadeProps {
  children: [React.ReactNode, React.ReactNode];
  delay?: number;
  duration?: number;
  easing?: string;
  style?: React.CSSProperties;
}

export const CrossFade: React.FC<CrossFadeProps> = ({
  children,
  delay = 0,
  duration = 30,
  easing,
  style,
}) => {
  const frame = useCurrentFrame();
  const customEasing = easing ? getEasingFromString(easing) : null;
  
  let progress = interpolate(
    frame,
    [delay, delay + duration],
    [0, 1],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );
  
  if (customEasing) {
    progress = customEasing(progress);
  }

  return (
    <div style={{ position: "relative", ...style }}>
      <div style={{ opacity: 1 - progress }}>
        {children[0]}
      </div>
      <div style={{ position: "absolute", inset: 0, opacity: progress }}>
        {children[1]}
      </div>
    </div>
  );
};

/**
 * BlurIn - Fade in with blur effect
 */
interface BlurInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  startBlur?: number;
  easing?: string;
  style?: React.CSSProperties;
}

export const BlurIn: React.FC<BlurInProps> = ({
  children,
  delay = 0,
  duration = 25,
  startBlur = 20,
  easing,
  style,
}) => {
  const frame = useCurrentFrame();
  const customEasing = easing ? getEasingFromString(easing) : null;
  
  let progress = interpolate(
    frame,
    [delay, delay + duration],
    [0, 1],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );
  
  if (customEasing) {
    progress = customEasing(progress);
  }

  const blur = interpolate(progress, [0, 1], [startBlur, 0]);

  return (
    <div
      style={{
        opacity: progress,
        filter: `blur(${blur}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
