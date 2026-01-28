/**
 * KenBurns & Image Transform Components - ENHANCED
 * 
 * Comprehensive image motion system with:
 * - Zoom + drift combos
 * - Micro-motion mode
 * - Keyframe-based pan paths
 * - Parallax layers
 * - Focus zoom with easing
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, Img, interpolate, Easing } from "remotion";
import { AbsoluteFill } from "remotion";
import { getEasingFromString } from "../lib/easing";

// ─────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────

type KenBurnsDirection = 
  | "zoom-in" 
  | "zoom-out" 
  | "pan-left" 
  | "pan-right" 
  | "pan-up" 
  | "pan-down"
  | "zoom-in-pan-left"
  | "zoom-in-pan-right"
  | "zoom-out-pan-left"
  | "zoom-out-pan-right"
  // NEW: Subtle motion types
  | "zoom-drift"
  | "subtle-drift"
  | "micro-motion"
  | "breathe";

interface PanKeyframe {
  frame: number;
  x: number;  // % position
  y: number;  // % position
  scale?: number;
  /** Optional pause duration at this keyframe */
  hold?: number;
}

// ─────────────────────────────────────────────────────────────
// KENBURNS - Enhanced with new motion types
// ─────────────────────────────────────────────────────────────

interface KenBurnsProps {
  src: string;
  direction?: KenBurnsDirection;
  intensity?: number;
  /** NEW: Custom easing string */
  easing?: string;
  /** NEW: Start and end scale for fine control */
  startScale?: number;
  endScale?: number;
  /** NEW: Drift amounts for zoom-drift mode */
  driftX?: number;
  driftY?: number;
  style?: React.CSSProperties;
}

export const KenBurns: React.FC<KenBurnsProps> = ({
  src,
  direction = "zoom-in",
  intensity = 1,
  easing,
  startScale,
  endScale,
  driftX = 2,
  driftY = 1,
  style,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  let progress = frame / durationInFrames;
  
  // Apply custom easing if provided
  const customEasing = easing ? getEasingFromString(easing) : null;
  if (customEasing) {
    progress = customEasing(progress);
  }

  // Base zoom range (modified by intensity)
  const zoomRange = 0.2 * intensity;
  const panRange = 5 * intensity;

  let scale = 1;
  let translateX = 0;
  let translateY = 0;

  switch (direction) {
    case "zoom-in":
      scale = startScale !== undefined && endScale !== undefined
        ? interpolate(progress, [0, 1], [startScale, endScale])
        : interpolate(progress, [0, 1], [1, 1 + zoomRange]);
      break;

    case "zoom-out":
      scale = startScale !== undefined && endScale !== undefined
        ? interpolate(progress, [0, 1], [startScale, endScale])
        : interpolate(progress, [0, 1], [1 + zoomRange, 1]);
      break;

    case "pan-left":
      translateX = interpolate(progress, [0, 1], [0, -panRange]);
      scale = 1.1;
      break;

    case "pan-right":
      translateX = interpolate(progress, [0, 1], [0, panRange]);
      scale = 1.1;
      break;

    case "pan-up":
      translateY = interpolate(progress, [0, 1], [0, -panRange]);
      scale = 1.1;
      break;

    case "pan-down":
      translateY = interpolate(progress, [0, 1], [0, panRange]);
      scale = 1.1;
      break;

    case "zoom-in-pan-left":
      scale = interpolate(progress, [0, 1], [1, 1 + zoomRange]);
      translateX = interpolate(progress, [0, 1], [0, -panRange * 0.5]);
      break;

    case "zoom-in-pan-right":
      scale = interpolate(progress, [0, 1], [1, 1 + zoomRange]);
      translateX = interpolate(progress, [0, 1], [0, panRange * 0.5]);
      break;

    case "zoom-out-pan-left":
      scale = interpolate(progress, [0, 1], [1 + zoomRange, 1]);
      translateX = interpolate(progress, [0, 1], [panRange * 0.5, 0]);
      break;

    case "zoom-out-pan-right":
      scale = interpolate(progress, [0, 1], [1 + zoomRange, 1]);
      translateX = interpolate(progress, [0, 1], [-panRange * 0.5, 0]);
      break;

    // NEW: Subtle motion types from RAG knowledge
    case "zoom-drift":
      // Combined zoom + drift (RAG: scale 1.0→1.02-1.03 + position 1-3%)
      const subtleZoom = 0.03 * intensity;
      scale = interpolate(progress, [0, 1], [1, 1 + subtleZoom]);
      translateX = interpolate(progress, [0, 1], [0, driftX * intensity]);
      translateY = interpolate(progress, [0, 1], [0, driftY * intensity]);
      break;

    case "subtle-drift":
      // Very gentle position shift only (RAG: 5-10px over full duration)
      scale = 1.02; // Slight zoom to hide edges
      translateX = interpolate(progress, [0, 1], [0, driftX * 0.5 * intensity]);
      translateY = interpolate(progress, [0, 1], [0, driftY * 0.5 * intensity]);
      break;

    case "micro-motion":
      // Barely perceptible movement (RAG: scale 0.98→1.0, slow drift)
      scale = interpolate(progress, [0, 1], [0.98, 1.0]);
      translateX = Math.sin(progress * Math.PI * 2) * 0.3 * intensity;
      translateY = Math.cos(progress * Math.PI * 2) * 0.2 * intensity;
      break;

    case "breathe":
      // Gentle scale oscillation
      scale = 1 + Math.sin(progress * Math.PI * 2) * 0.015 * intensity;
      break;
  }

  return (
    <AbsoluteFill style={{ overflow: "hidden", ...style }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translate(${translateX}%, ${translateY}%)`,
        }}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// KEYFRAME PAN - NEW (complex pan paths with pauses)
// ─────────────────────────────────────────────────────────────

interface KeyframePanProps {
  src: string;
  /** Array of keyframes defining the pan path */
  keyframes: PanKeyframe[];
  /** Custom easing between keyframes */
  easing?: string;
  style?: React.CSSProperties;
}

export const KeyframePan: React.FC<KeyframePanProps> = ({
  src,
  keyframes,
  easing,
  style,
}) => {
  const frame = useCurrentFrame();
  const customEasing = easing ? getEasingFromString(easing) : null;

  // Sort keyframes by frame
  const sortedKeyframes = [...keyframes].sort((a, b) => a.frame - b.frame);
  
  // Find current segment
  let currentIndex = 0;
  for (let i = 0; i < sortedKeyframes.length - 1; i++) {
    const kf = sortedKeyframes[i];
    const nextKf = sortedKeyframes[i + 1];
    const holdEnd = kf.frame + (kf.hold ?? 0);
    
    if (frame >= kf.frame && frame < nextKf.frame) {
      currentIndex = i;
      break;
    }
    if (i === sortedKeyframes.length - 2) {
      currentIndex = i;
    }
  }

  const currentKf = sortedKeyframes[currentIndex];
  const nextKf = sortedKeyframes[currentIndex + 1] ?? currentKf;
  
  // Calculate progress within segment, accounting for hold
  const holdDuration = currentKf.hold ?? 0;
  const segmentStart = currentKf.frame + holdDuration;
  const segmentEnd = nextKf.frame;
  const segmentDuration = segmentEnd - segmentStart;
  
  let segmentProgress: number;
  if (frame < segmentStart) {
    // In hold period
    segmentProgress = 0;
  } else if (segmentDuration <= 0) {
    segmentProgress = 1;
  } else {
    segmentProgress = Math.min(1, (frame - segmentStart) / segmentDuration);
  }
  
  // Apply easing
  if (customEasing) {
    segmentProgress = customEasing(segmentProgress);
  }

  // Interpolate values
  const x = interpolate(segmentProgress, [0, 1], [currentKf.x, nextKf.x]);
  const y = interpolate(segmentProgress, [0, 1], [currentKf.y, nextKf.y]);
  const scale = interpolate(
    segmentProgress, 
    [0, 1], 
    [currentKf.scale ?? 1, nextKf.scale ?? 1]
  );

  // Convert position to transform (50,50 = centered, no translate)
  const translateX = (x - 50) * -0.1;
  const translateY = (y - 50) * -0.1;

  return (
    <AbsoluteFill style={{ overflow: "hidden", ...style }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translate(${translateX}%, ${translateY}%)`,
          transformOrigin: `${x}% ${y}%`,
        }}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// FOCUS ZOOM - Enhanced with easing
// ─────────────────────────────────────────────────────────────

interface FocusZoomProps {
  src: string;
  focusX?: number;
  focusY?: number;
  startScale?: number;
  endScale?: number;
  /** NEW: Custom easing */
  easing?: string;
  /** NEW: Delay before zoom starts */
  delay?: number;
  /** NEW: Duration of zoom (frames, default full clip) */
  duration?: number;
  style?: React.CSSProperties;
}

export const FocusZoom: React.FC<FocusZoomProps> = ({
  src,
  focusX = 50,
  focusY = 50,
  startScale = 1,
  endScale = 1.3,
  easing,
  delay = 0,
  duration,
  style,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const effectiveDuration = duration ?? (durationInFrames - delay);
  const effectiveFrame = Math.max(0, frame - delay);
  let progress = Math.min(1, effectiveFrame / effectiveDuration);

  // Apply custom easing
  const customEasing = easing ? getEasingFromString(easing) : null;
  if (customEasing) {
    progress = customEasing(progress);
  }

  const scale = interpolate(progress, [0, 1], [startScale, endScale]);

  const translateX = (50 - focusX) * (scale - 1);
  const translateY = (50 - focusY) * (scale - 1);

  return (
    <AbsoluteFill style={{ overflow: "hidden", ...style }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translate(${translateX}%, ${translateY}%)`,
          transformOrigin: `${focusX}% ${focusY}%`,
        }}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// PARALLAX IMAGE - Enhanced with layers
// ─────────────────────────────────────────────────────────────

type ParallaxLayer = "background" | "content" | "foreground";

interface ParallaxImageProps {
  src: string;
  speed?: number;
  direction?: "horizontal" | "vertical";
  /** NEW: Predefined layer speeds (RAG: bg 2%, content 4%, fg 8%) */
  layer?: ParallaxLayer;
  /** NEW: Custom easing */
  easing?: string;
  /** NEW: Reverse direction */
  reverse?: boolean;
  style?: React.CSSProperties;
}

const PARALLAX_LAYER_SPEEDS: Record<ParallaxLayer, number> = {
  background: 0.25,   // 2% position shift
  content: 0.5,       // 4% position shift
  foreground: 1.0,    // 8% position shift
};

export const ParallaxImage: React.FC<ParallaxImageProps> = ({
  src,
  speed,
  direction = "vertical",
  layer,
  easing,
  reverse = false,
  style,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  let progress = frame / durationInFrames;
  
  const customEasing = easing ? getEasingFromString(easing) : null;
  if (customEasing) {
    progress = customEasing(progress);
  }

  const effectiveSpeed = speed ?? (layer ? PARALLAX_LAYER_SPEEDS[layer] : 0.5);
  const multiplier = reverse ? -1 : 1;
  const offset = progress * 20 * effectiveSpeed * multiplier;

  const transform = direction === "vertical"
    ? `translateY(${-offset}%)`
    : `translateX(${-offset}%)`;

  return (
    <AbsoluteFill style={{ overflow: "hidden", ...style }}>
      <Img
        src={src}
        style={{
          width: direction === "horizontal" ? "120%" : "100%",
          height: direction === "vertical" ? "120%" : "100%",
          objectFit: "cover",
          transform,
        }}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// CINEMATIC PAN - NEW (slow, dramatic panning)
// ─────────────────────────────────────────────────────────────

interface CinematicPanProps {
  src: string;
  /** Start position (percentage from left/top) */
  startX?: number;
  startY?: number;
  /** End position */
  endX?: number;
  endY?: number;
  /** Scale during pan */
  scale?: number;
  /** Custom easing */
  easing?: string;
  style?: React.CSSProperties;
}

export const CinematicPan: React.FC<CinematicPanProps> = ({
  src,
  startX = 30,
  startY = 50,
  endX = 70,
  endY = 50,
  scale = 1.2,
  easing = "elegantSmooth",
  style,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  let progress = frame / durationInFrames;
  
  const customEasing = easing ? getEasingFromString(easing) : null;
  if (customEasing) {
    progress = customEasing(progress);
  }

  const x = interpolate(progress, [0, 1], [startX, endX]);
  const y = interpolate(progress, [0, 1], [startY, endY]);

  return (
    <AbsoluteFill style={{ overflow: "hidden", ...style }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
          transformOrigin: `${x}% ${y}%`,
        }}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// REVEAL IMAGE - NEW (image reveals with mask)
// ─────────────────────────────────────────────────────────────

interface RevealImageProps {
  src: string;
  direction?: "left" | "right" | "top" | "bottom" | "center";
  delay?: number;
  duration?: number;
  /** Apply Ken Burns after reveal */
  afterReveal?: KenBurnsDirection;
  afterRevealIntensity?: number;
  easing?: string;
  style?: React.CSSProperties;
}

export const RevealImage: React.FC<RevealImageProps> = ({
  src,
  direction = "left",
  delay = 0,
  duration = 30,
  afterReveal,
  afterRevealIntensity = 0.5,
  easing,
  style,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const effectiveFrame = Math.max(0, frame - delay);
  let revealProgress = Math.min(1, effectiveFrame / duration);
  
  const customEasing = easing ? getEasingFromString(easing) : null;
  if (customEasing) {
    revealProgress = customEasing(revealProgress);
  }

  // Calculate clip path based on direction
  const getClipPath = () => {
    const p = revealProgress * 100;
    switch (direction) {
      case "left":
        return `inset(0 ${100 - p}% 0 0)`;
      case "right":
        return `inset(0 0 0 ${100 - p}%)`;
      case "top":
        return `inset(0 0 ${100 - p}% 0)`;
      case "bottom":
        return `inset(${100 - p}% 0 0 0)`;
      case "center":
        const half = (100 - p) / 2;
        return `inset(${half}% ${half}% ${half}% ${half}%)`;
    }
  };

  // Calculate Ken Burns transform if specified
  let transform = "";
  if (afterReveal && revealProgress >= 1) {
    const kenBurnsFrame = effectiveFrame - duration;
    const kenBurnsDuration = durationInFrames - delay - duration;
    const kenBurnsProgress = Math.min(1, kenBurnsFrame / kenBurnsDuration);
    
    const zoomRange = 0.2 * afterRevealIntensity;
    
    switch (afterReveal) {
      case "zoom-in":
        const scale = 1 + kenBurnsProgress * zoomRange;
        transform = `scale(${scale})`;
        break;
      case "zoom-out":
        const scaleOut = 1 + zoomRange - kenBurnsProgress * zoomRange;
        transform = `scale(${scaleOut})`;
        break;
      // Add more as needed
    }
  }

  return (
    <AbsoluteFill style={{ overflow: "hidden", ...style }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          clipPath: getClipPath(),
          transform: transform || undefined,
        }}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// SPLIT SCREEN - NEW (multiple images with transitions)
// ─────────────────────────────────────────────────────────────

interface SplitScreenProps {
  images: Array<{
    src: string;
    kenBurns?: KenBurnsDirection;
    intensity?: number;
  }>;
  /** Split direction */
  direction?: "horizontal" | "vertical";
  /** Gap between splits */
  gap?: number;
  /** Stagger reveal */
  staggerDelay?: number;
  style?: React.CSSProperties;
}

export const SplitScreen: React.FC<SplitScreenProps> = ({
  images,
  direction = "horizontal",
  gap = 4,
  staggerDelay = 5,
  style,
}) => {
  const frame = useCurrentFrame();
  const count = images.length;
  const sizePercent = (100 - gap * (count - 1)) / count;

  return (
    <AbsoluteFill 
      style={{ 
        display: "flex", 
        flexDirection: direction === "horizontal" ? "row" : "column",
        gap,
        overflow: "hidden",
        ...style,
      }}
    >
      {images.map((img, i) => {
        const revealProgress = Math.min(1, Math.max(0, (frame - i * staggerDelay) / 20));
        
        return (
          <div
            key={i}
            style={{
              flex: `0 0 ${sizePercent}%`,
              overflow: "hidden",
              opacity: revealProgress,
              transform: `scale(${0.9 + revealProgress * 0.1})`,
            }}
          >
            {img.kenBurns ? (
              <KenBurns 
                src={img.src} 
                direction={img.kenBurns} 
                intensity={img.intensity ?? 0.5}
              />
            ) : (
              <Img
                src={img.src}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
