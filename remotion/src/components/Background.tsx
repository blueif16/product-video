/**
 * Background Components
 * 
 * Reusable animated backgrounds for scenes.
 */

import React from "react";
import { useCurrentFrame, interpolate, AbsoluteFill } from "remotion";
import { theme } from "../lib/theme";

/**
 * GradientBackground - Animated gradient
 */
interface GradientBackgroundProps {
  colors?: string[];
  angle?: number;
  animate?: boolean;
  style?: React.CSSProperties;
}

export const GradientBackground: React.FC<GradientBackgroundProps> = ({
  colors = [theme.colors.background, theme.colors.backgroundDark],
  angle = 180,
  animate = false,
  style,
}) => {
  const frame = useCurrentFrame();

  const animatedAngle = animate 
    ? angle + Math.sin(frame / 100) * 20 
    : angle;

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${animatedAngle}deg, ${colors.join(", ")})`,
        ...style,
      }}
    />
  );
};

/**
 * GlowingOrb - Animated glowing orb for backgrounds
 */
interface GlowingOrbProps {
  color?: string;
  size?: number;
  x?: number;
  y?: number;
  delay?: number;
  pulseSpeed?: number;
}

export const GlowingOrb: React.FC<GlowingOrbProps> = ({
  color = theme.colors.primary,
  size = 400,
  x = 50,
  y = 50,
  delay = 0,
  pulseSpeed = 20,
}) => {
  const frame = useCurrentFrame();

  const pulse = interpolate(
    Math.sin((frame + delay * 10) / pulseSpeed),
    [-1, 1],
    [0.8, 1.2]
  );

  const drift = {
    x: Math.sin((frame + delay * 5) / 60) * 2,
    y: Math.cos((frame + delay * 5) / 60) * 2,
  };

  return (
    <div
      style={{
        position: "absolute",
        left: `${x + drift.x}%`,
        top: `${y + drift.y}%`,
        width: size,
        height: size,
        borderRadius: "50%",
        background: `radial-gradient(circle, ${color}40 0%, transparent 70%)`,
        transform: `translate(-50%, -50%) scale(${pulse})`,
        filter: "blur(40px)",
        pointerEvents: "none",
      }}
    />
  );
};

/**
 * OrbsBackground - Multiple animated orbs
 */
interface OrbsBackgroundProps {
  orbs?: Array<{
    color: string;
    size: number;
    x: number;
    y: number;
  }>;
  baseColor?: string;
}

export const OrbsBackground: React.FC<OrbsBackgroundProps> = ({
  orbs = [
    { color: theme.colors.primary, size: 600, x: 20, y: 30 },
    { color: theme.colors.accent, size: 400, x: 80, y: 70 },
    { color: theme.colors.accentAlt, size: 500, x: 60, y: 20 },
  ],
  baseColor = theme.colors.background,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: baseColor, overflow: "hidden" }}>
      {orbs.map((orb, i) => (
        <GlowingOrb
          key={i}
          color={orb.color}
          size={orb.size}
          x={orb.x}
          y={orb.y}
          delay={i * 10}
        />
      ))}
    </AbsoluteFill>
  );
};

/**
 * GridBackground - Subtle grid pattern
 */
interface GridBackgroundProps {
  color?: string;
  lineColor?: string;
  gridSize?: number;
  animated?: boolean;
}

export const GridBackground: React.FC<GridBackgroundProps> = ({
  color = theme.colors.background,
  lineColor = theme.colors.overlayLight,
  gridSize = 40,
  animated = false,
}) => {
  const frame = useCurrentFrame();
  
  const offset = animated ? (frame % gridSize) : 0;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: color,
        backgroundImage: `
          linear-gradient(${lineColor} 1px, transparent 1px),
          linear-gradient(90deg, ${lineColor} 1px, transparent 1px)
        `,
        backgroundSize: `${gridSize}px ${gridSize}px`,
        backgroundPosition: `${offset}px ${offset}px`,
      }}
    />
  );
};

/**
 * NoiseBackground - Subtle noise texture
 */
interface NoiseBackgroundProps {
  color?: string;
  opacity?: number;
}

export const NoiseBackground: React.FC<NoiseBackgroundProps> = ({
  color = theme.colors.background,
  opacity = 0.05,
}) => {
  // Generate a simple noise pattern using CSS
  // For production, consider using an actual noise texture image
  return (
    <AbsoluteFill style={{ backgroundColor: color }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%' height='100%' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * RadialGradientBackground - Centered radial gradient
 */
interface RadialGradientBackgroundProps {
  centerColor?: string;
  edgeColor?: string;
  centerX?: number;
  centerY?: number;
}

export const RadialGradientBackground: React.FC<RadialGradientBackgroundProps> = ({
  centerColor = theme.colors.backgroundLight,
  edgeColor = theme.colors.backgroundDark,
  centerX = 50,
  centerY = 50,
}) => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at ${centerX}% ${centerY}%, ${centerColor} 0%, ${edgeColor} 100%)`,
      }}
    />
  );
};
