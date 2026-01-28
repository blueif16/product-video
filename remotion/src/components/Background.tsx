/**
 * Background Components - ENHANCED
 * 
 * Comprehensive animated backgrounds with full customization.
 * Includes: Orbs, Gradients, Mesh, Grid, Noise, Radial
 */

import React from "react";
import { useCurrentFrame, interpolate, AbsoluteFill } from "remotion";
import { theme } from "../lib/theme";

// ─────────────────────────────────────────────────────────────
// GRADIENT BACKGROUND - Enhanced with angle animation range
// ─────────────────────────────────────────────────────────────

interface GradientBackgroundProps {
  colors?: string[];
  angle?: number;
  animate?: boolean;
  /** NEW: Custom animation range [startAngle, endAngle] */
  animateAngleRange?: [number, number];
  /** NEW: Animation speed in frames per cycle */
  animateSpeed?: number;
  style?: React.CSSProperties;
}

export const GradientBackground: React.FC<GradientBackgroundProps> = ({
  colors = [theme.colors.background, theme.colors.backgroundDark],
  angle = 180,
  animate = false,
  animateAngleRange,
  animateSpeed = 200,
  style,
}) => {
  const frame = useCurrentFrame();

  let animatedAngle = angle;
  
  if (animate) {
    if (animateAngleRange) {
      // Custom range: interpolate between start and end angles
      const progress = (Math.sin(frame / animateSpeed * Math.PI * 2) + 1) / 2;
      animatedAngle = interpolate(progress, [0, 1], animateAngleRange);
    } else {
      // Default: ±20° oscillation
      animatedAngle = angle + Math.sin(frame / 100) * 20;
    }
  }

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${animatedAngle}deg, ${colors.join(", ")})`,
        ...style,
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────
// GLOWING ORB - Enhanced with full customization
// ─────────────────────────────────────────────────────────────

interface GlowingOrbProps {
  color?: string;
  size?: number;
  x?: number;
  y?: number;
  delay?: number;
  pulseSpeed?: number;
  /** NEW: Orb opacity 0-1 (RAG: 30-50% recommended) */
  opacity?: number;
  /** NEW: Blur amount in pixels (RAG: 40-80px) */
  blur?: number;
  /** NEW: Drift speed 0-10 scale (RAG: 3-8% canvas position) */
  driftSpeed?: number;
  /** NEW: Max drift distance as % of canvas */
  maxDrift?: number;
}

export const GlowingOrb: React.FC<GlowingOrbProps> = ({
  color = theme.colors.primary,
  size = 400,
  x = 50,
  y = 50,
  delay = 0,
  pulseSpeed = 20,
  opacity = 0.4,         // RAG default: 30-50%
  blur = 60,             // RAG default: 40-80px
  driftSpeed = 5,        // RAG default: 3-8% drift
  maxDrift = 4,          // Max drift as % of canvas
}) => {
  const frame = useCurrentFrame();

  // Pulse animation
  const pulse = interpolate(
    Math.sin((frame + delay * 10) / pulseSpeed),
    [-1, 1],
    [0.85, 1.15]
  );

  // Drift animation - scaled by driftSpeed
  const driftMultiplier = driftSpeed / 5; // Normalize to 1 at default
  const drift = {
    x: Math.sin((frame + delay * 5) / 60) * maxDrift * driftMultiplier,
    y: Math.cos((frame + delay * 5) / 60) * maxDrift * driftMultiplier,
  };

  // Convert hex color to rgba for proper opacity handling
  const getColorWithOpacity = (hexColor: string, alpha: number): string => {
    // If already rgba, replace alpha
    if (hexColor.startsWith("rgba")) {
      return hexColor.replace(/[\d.]+\)$/, `${alpha})`);
    }
    // If rgb, convert to rgba
    if (hexColor.startsWith("rgb(")) {
      return hexColor.replace("rgb(", "rgba(").replace(")", `, ${alpha})`);
    }
    // If hex, convert
    if (hexColor.startsWith("#")) {
      const hex = hexColor.slice(1);
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    return hexColor;
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
        background: `radial-gradient(circle, ${getColorWithOpacity(color, opacity)} 0%, transparent 70%)`,
        transform: `translate(-50%, -50%) scale(${pulse})`,
        filter: `blur(${blur}px)`,
        pointerEvents: "none",
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────
// ORBS BACKGROUND - Enhanced with full configuration
// ─────────────────────────────────────────────────────────────

interface OrbConfig {
  color: string;
  size: number;
  x: number;
  y: number;
}

interface OrbsBackgroundProps {
  orbs?: OrbConfig[];
  baseColor?: string;
  /** NEW: Override orb count (generates positions automatically) */
  orbCount?: number;
  /** NEW: Override orb colors (cycles through if more orbs than colors) */
  orbColors?: string[];
  /** NEW: Manual orb positions [{x, y}] */
  orbPositions?: Array<{ x: number; y: number }>;
  /** NEW: Global opacity for all orbs */
  orbOpacity?: number;
  /** NEW: Global blur for all orbs */
  orbBlur?: number;
  /** NEW: Global drift speed for all orbs */
  orbDriftSpeed?: number;
  /** NEW: Size range for auto-generated orbs */
  sizeRange?: [number, number];
}

// Default positions for orbs (corners and edges, not center - per RAG)
const DEFAULT_ORB_POSITIONS = [
  { x: 15, y: 20 },   // Top-left area
  { x: 85, y: 25 },   // Top-right area  
  { x: 20, y: 80 },   // Bottom-left area
  { x: 80, y: 75 },   // Bottom-right area
  { x: 50, y: 10 },   // Top edge
  { x: 10, y: 50 },   // Left edge
  { x: 90, y: 50 },   // Right edge
];

export const OrbsBackground: React.FC<OrbsBackgroundProps> = ({
  orbs,
  baseColor = theme.colors.background,
  orbCount,
  orbColors,
  orbPositions,
  orbOpacity = 0.4,
  orbBlur = 60,
  orbDriftSpeed = 5,
  sizeRange = [350, 600],
}) => {
  // Determine orbs to render
  let finalOrbs: OrbConfig[];
  
  if (orbs) {
    // Use provided orbs directly
    finalOrbs = orbs;
  } else {
    // Generate orbs from parameters
    const count = orbCount ?? orbColors?.length ?? 3;
    const colors = orbColors ?? [
      theme.colors.primary,
      theme.colors.accent,
      theme.colors.accentAlt,
    ];
    const positions = orbPositions ?? DEFAULT_ORB_POSITIONS;
    
    finalOrbs = Array.from({ length: Math.min(count, 7) }, (_, i) => ({
      color: colors[i % colors.length],
      size: sizeRange[0] + ((sizeRange[1] - sizeRange[0]) * (i / Math.max(1, count - 1))),
      x: positions[i % positions.length].x,
      y: positions[i % positions.length].y,
    }));
  }

  return (
    <AbsoluteFill style={{ backgroundColor: baseColor, overflow: "hidden" }}>
      {finalOrbs.map((orb, i) => (
        <GlowingOrb
          key={i}
          color={orb.color}
          size={orb.size}
          x={orb.x}
          y={orb.y}
          delay={i * 10}
          opacity={orbOpacity}
          blur={orbBlur}
          driftSpeed={orbDriftSpeed}
        />
      ))}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// MESH GRADIENT BACKGROUND - NEW (from RAG knowledge)
// ─────────────────────────────────────────────────────────────

interface MeshPoint {
  x: number;        // 0-100 percentage
  y: number;        // 0-100 percentage
  color: string;
  size?: number;    // Radius of gradient in pixels
  blur?: number;    // Additional blur
}

interface MeshGradientBackgroundProps {
  /** Color points with positions (RAG: 4-7 points recommended) */
  points: MeshPoint[];
  /** Base background color */
  baseColor?: string;
  /** Animate point positions */
  animate?: boolean;
  /** Animation drift amount */
  driftAmount?: number;
  /** Animation speed */
  animationSpeed?: number;
  style?: React.CSSProperties;
}

export const MeshGradientBackground: React.FC<MeshGradientBackgroundProps> = ({
  points,
  baseColor = theme.colors.backgroundDark,
  animate = false,
  driftAmount = 3,
  animationSpeed = 80,
  style,
}) => {
  const frame = useCurrentFrame();

  // Calculate animated positions
  const getAnimatedPosition = (point: MeshPoint, index: number) => {
    if (!animate) return { x: point.x, y: point.y };
    
    const phase = (frame + index * 20) / animationSpeed;
    return {
      x: point.x + Math.sin(phase) * driftAmount,
      y: point.y + Math.cos(phase * 0.7) * driftAmount,
    };
  };

  return (
    <AbsoluteFill style={{ backgroundColor: baseColor, overflow: "hidden", ...style }}>
      {points.map((point, i) => {
        const pos = getAnimatedPosition(point, i);
        const size = point.size ?? 500;
        const blur = point.blur ?? 80;
        
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              width: size,
              height: size,
              borderRadius: "50%",
              background: `radial-gradient(circle, ${point.color} 0%, transparent 70%)`,
              transform: "translate(-50%, -50%)",
              filter: `blur(${blur}px)`,
              opacity: 0.6,
              pointerEvents: "none",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// GRID BACKGROUND - Enhanced
// ─────────────────────────────────────────────────────────────

interface GridBackgroundProps {
  color?: string;
  lineColor?: string;
  gridSize?: number;
  animated?: boolean;
  /** NEW: Line thickness */
  lineWidth?: number;
  /** NEW: Fade at edges */
  fadeEdges?: boolean;
  /** NEW: Perspective tilt */
  perspective?: boolean;
  /** NEW: Animation speed (frames per grid cycle) */
  animationSpeed?: number;
}

export const GridBackground: React.FC<GridBackgroundProps> = ({
  color = theme.colors.background,
  lineColor = theme.colors.overlayLight,
  gridSize = 40,
  animated = false,
  lineWidth = 1,
  fadeEdges = false,
  perspective = false,
  animationSpeed,
}) => {
  const frame = useCurrentFrame();
  
  const speed = animationSpeed ?? gridSize;
  const offset = animated ? (frame % speed) * (gridSize / speed) : 0;

  const containerStyle: React.CSSProperties = {
    backgroundColor: color,
    backgroundImage: `
      linear-gradient(${lineColor} ${lineWidth}px, transparent ${lineWidth}px),
      linear-gradient(90deg, ${lineColor} ${lineWidth}px, transparent ${lineWidth}px)
    `,
    backgroundSize: `${gridSize}px ${gridSize}px`,
    backgroundPosition: `${offset}px ${offset}px`,
  };

  if (perspective) {
    containerStyle.transform = "perspective(500px) rotateX(60deg)";
    containerStyle.transformOrigin = "center bottom";
  }

  const content = <AbsoluteFill style={containerStyle} />;

  if (fadeEdges) {
    return (
      <AbsoluteFill style={{ backgroundColor: color }}>
        {content}
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at center, transparent 30%, ${color} 100%)`,
          }}
        />
      </AbsoluteFill>
    );
  }

  return content;
};

// ─────────────────────────────────────────────────────────────
// NOISE BACKGROUND
// ─────────────────────────────────────────────────────────────

interface NoiseBackgroundProps {
  color?: string;
  opacity?: number;
  /** NEW: Noise grain size */
  grainSize?: "fine" | "medium" | "coarse";
  /** NEW: Animate noise */
  animate?: boolean;
}

export const NoiseBackground: React.FC<NoiseBackgroundProps> = ({
  color = theme.colors.background,
  opacity = 0.05,
  grainSize = "medium",
  animate = false,
}) => {
  const frame = useCurrentFrame();
  
  const baseFrequency = {
    fine: "0.9",
    medium: "0.65",
    coarse: "0.4",
  }[grainSize];
  
  // Animate by slightly varying the seed
  const seed = animate ? Math.floor(frame / 2) % 100 : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: color }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='${baseFrequency}' numOctaves='3' seed='${seed}' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// RADIAL GRADIENT BACKGROUND - Enhanced
// ─────────────────────────────────────────────────────────────

interface RadialGradientBackgroundProps {
  centerColor?: string;
  edgeColor?: string;
  centerX?: number;
  centerY?: number;
  /** NEW: Animate center position */
  animate?: boolean;
  /** NEW: Animation drift range */
  driftRange?: number;
  /** NEW: Gradient shape */
  shape?: "circle" | "ellipse";
  /** NEW: Gradient size */
  size?: "closest-side" | "farthest-side" | "closest-corner" | "farthest-corner";
}

export const RadialGradientBackground: React.FC<RadialGradientBackgroundProps> = ({
  centerColor = theme.colors.backgroundLight,
  edgeColor = theme.colors.backgroundDark,
  centerX = 50,
  centerY = 50,
  animate = false,
  driftRange = 5,
  shape = "ellipse",
  size = "farthest-corner",
}) => {
  const frame = useCurrentFrame();
  
  let x = centerX;
  let y = centerY;
  
  if (animate) {
    x = centerX + Math.sin(frame / 100) * driftRange;
    y = centerY + Math.cos(frame / 80) * driftRange;
  }

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(${shape} ${size} at ${x}% ${y}%, ${centerColor} 0%, ${edgeColor} 100%)`,
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────
// AURORA BACKGROUND - NEW (bonus)
// ─────────────────────────────────────────────────────────────

interface AuroraBackgroundProps {
  colors?: string[];
  baseColor?: string;
  speed?: number;
  intensity?: number;
}

export const AuroraBackground: React.FC<AuroraBackgroundProps> = ({
  colors = ["#6366f1", "#ec4899", "#06b6d4", "#22c55e"],
  baseColor = theme.colors.backgroundDark,
  speed = 100,
  intensity = 0.6,
}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: baseColor, overflow: "hidden" }}>
      {colors.map((color, i) => {
        const phase = (frame + i * 30) / speed;
        const x = 50 + Math.sin(phase * (0.5 + i * 0.1)) * 40;
        const y = 30 + Math.sin(phase * (0.3 + i * 0.1)) * 20;
        
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `${y}%`,
              width: 800,
              height: 400,
              borderRadius: "50%",
              background: `radial-gradient(ellipse, ${color} 0%, transparent 70%)`,
              transform: `translate(-50%, -50%) rotate(${phase * 10 + i * 45}deg)`,
              filter: "blur(60px)",
              opacity: intensity * 0.5,
              pointerEvents: "none",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// PARTICLES BACKGROUND - NEW (bonus)
// ─────────────────────────────────────────────────────────────

interface Particle {
  x: number;
  y: number;
  size: number;
  speed: number;
  opacity: number;
}

interface ParticlesBackgroundProps {
  count?: number;
  color?: string;
  baseColor?: string;
  minSize?: number;
  maxSize?: number;
  direction?: "up" | "down" | "left" | "right";
}

export const ParticlesBackground: React.FC<ParticlesBackgroundProps> = ({
  count = 50,
  color = "#ffffff",
  baseColor = theme.colors.backgroundDark,
  minSize = 2,
  maxSize = 6,
  direction = "up",
}) => {
  const frame = useCurrentFrame();
  
  // Generate deterministic particles
  const particles: Particle[] = React.useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      x: (Math.sin(i * 7.13) * 0.5 + 0.5) * 100,
      y: (Math.cos(i * 11.17) * 0.5 + 0.5) * 100,
      size: minSize + (Math.sin(i * 3.14) * 0.5 + 0.5) * (maxSize - minSize),
      speed: 0.3 + (Math.sin(i * 5.67) * 0.5 + 0.5) * 0.7,
      opacity: 0.3 + (Math.sin(i * 2.34) * 0.5 + 0.5) * 0.5,
    }));
  }, [count, minSize, maxSize]);

  return (
    <AbsoluteFill style={{ backgroundColor: baseColor, overflow: "hidden" }}>
      {particles.map((particle, i) => {
        const movement = frame * particle.speed * 0.5;
        let x = particle.x;
        let y = particle.y;
        
        switch (direction) {
          case "up":
            y = ((particle.y - movement) % 120 + 120) % 120 - 10;
            break;
          case "down":
            y = ((particle.y + movement) % 120 + 120) % 120 - 10;
            break;
          case "left":
            x = ((particle.x - movement) % 120 + 120) % 120 - 10;
            break;
          case "right":
            x = ((particle.x + movement) % 120 + 120) % 120 - 10;
            break;
        }
        
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `${y}%`,
              width: particle.size,
              height: particle.size,
              borderRadius: "50%",
              backgroundColor: color,
              opacity: particle.opacity,
              pointerEvents: "none",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
