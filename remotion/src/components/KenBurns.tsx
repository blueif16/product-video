/**
 * KenBurns Component
 * 
 * Cinematic zoom and pan effect for images.
 * Named after documentary filmmaker Ken Burns.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, Img, interpolate } from "remotion";
import { AbsoluteFill } from "remotion";

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
  | "zoom-out-pan-right";

interface KenBurnsProps {
  src: string;
  direction?: KenBurnsDirection;
  intensity?: number;
  style?: React.CSSProperties;
}

export const KenBurns: React.FC<KenBurnsProps> = ({
  src,
  direction = "zoom-in",
  intensity = 1,
  style,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const progress = frame / durationInFrames;

  // Base zoom range (modified by intensity)
  const zoomRange = 0.2 * intensity;
  const panRange = 5 * intensity; // percentage

  let scale = 1;
  let translateX = 0;
  let translateY = 0;

  switch (direction) {
    case "zoom-in":
      scale = interpolate(progress, [0, 1], [1, 1 + zoomRange]);
      break;

    case "zoom-out":
      scale = interpolate(progress, [0, 1], [1 + zoomRange, 1]);
      break;

    case "pan-left":
      translateX = interpolate(progress, [0, 1], [0, -panRange]);
      scale = 1.1; // Slight zoom to hide edges
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

/**
 * FocusZoom - Zoom towards a specific point
 */
interface FocusZoomProps {
  src: string;
  focusX?: number; // 0-100, percentage from left
  focusY?: number; // 0-100, percentage from top
  startScale?: number;
  endScale?: number;
  style?: React.CSSProperties;
}

export const FocusZoom: React.FC<FocusZoomProps> = ({
  src,
  focusX = 50,
  focusY = 50,
  startScale = 1,
  endScale = 1.3,
  style,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const progress = frame / durationInFrames;

  const scale = interpolate(progress, [0, 1], [startScale, endScale]);

  // Calculate translation to keep focus point centered as we zoom
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

/**
 * ParallaxImage - Parallax scrolling effect
 */
interface ParallaxImageProps {
  src: string;
  speed?: number; // 0.5 = half speed, 2 = double speed
  direction?: "horizontal" | "vertical";
  style?: React.CSSProperties;
}

export const ParallaxImage: React.FC<ParallaxImageProps> = ({
  src,
  speed = 0.5,
  direction = "vertical",
  style,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const progress = frame / durationInFrames;
  const offset = progress * 20 * speed; // Max 20% movement

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
