/**
 * ConnectorLine Component
 * 
 * Animated connector lines for callouts, feature annotations, and diagrams.
 * Supports SVG line drawing animation with various styles.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { AbsoluteFill } from "remotion";
import { SPRING_CONFIGS, AnimationFeel, getEasingFromString } from "../lib/easing";

// ─────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────

interface Point {
  x: number;  // Percentage 0-100
  y: number;  // Percentage 0-100
}

type LineStyle = "solid" | "dashed" | "dotted";
type LineEnd = "none" | "arrow" | "dot" | "diamond";

// ─────────────────────────────────────────────────────────────
// CONNECTOR LINE
// ─────────────────────────────────────────────────────────────

interface ConnectorLineProps {
  /** Start point (percentage coordinates) */
  from: Point;
  /** End point (percentage coordinates) */
  to: Point;
  /** Optional waypoints for curved/bent lines */
  waypoints?: Point[];
  /** Line color */
  color?: string;
  /** Line thickness */
  strokeWidth?: number;
  /** Line style */
  lineStyle?: LineStyle;
  /** Start decoration */
  startEnd?: LineEnd;
  /** End decoration */
  endEnd?: LineEnd;
  /** Animation delay in frames */
  delay?: number;
  /** Animation duration in frames */
  duration?: number;
  /** Draw direction */
  direction?: "forward" | "reverse" | "both";
  /** Animation feel */
  feel?: AnimationFeel;
  /** Custom easing */
  easing?: string;
  /** Glow effect */
  glow?: boolean;
  glowColor?: string;
  glowIntensity?: number;
  /** Z-index */
  zIndex?: number;
}

export const ConnectorLine: React.FC<ConnectorLineProps> = ({
  from,
  to,
  waypoints = [],
  color = "#ffffff",
  strokeWidth = 2,
  lineStyle = "solid",
  startEnd = "none",
  endEnd = "arrow",
  delay = 0,
  duration = 30,
  direction = "forward",
  feel = "smooth",
  easing,
  glow = false,
  glowColor,
  glowIntensity = 1,
  zIndex = 100,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Defensive check: ensure from and to are valid
  if (!from || !to || typeof from.x !== 'number' || typeof from.y !== 'number' ||
      typeof to.x !== 'number' || typeof to.y !== 'number') {
    console.error('ConnectorLine: Invalid from/to points', { from, to });
    return null;
  }

  // Calculate animation progress
  const effectiveFrame = Math.max(0, frame - delay);
  let progress: number;

  if (easing) {
    const customEasing = getEasingFromString(easing);
    progress = customEasing
      ? customEasing(Math.min(1, effectiveFrame / duration))
      : Math.min(1, effectiveFrame / duration);
  } else {
    progress = spring({
      frame: effectiveFrame,
      fps,
      config: SPRING_CONFIGS[feel],
    });
  }

  // Convert percentage to pixels
  const toPx = (point: Point) => ({
    x: (point.x / 100) * width,
    y: (point.y / 100) * height,
  });

  const fromPx = toPx(from);
  const toPx_ = toPx(to);
  const waypointsPx = waypoints.filter(p => p && typeof p.x === 'number' && typeof p.y === 'number').map(toPx);

  // Build path
  let pathD: string;
  if (waypointsPx.length === 0) {
    // Simple straight line
    pathD = `M ${fromPx.x} ${fromPx.y} L ${toPx_.x} ${toPx_.y}`;
  } else if (waypointsPx.length === 1) {
    // Quadratic curve through waypoint
    const wp = waypointsPx[0];
    pathD = `M ${fromPx.x} ${fromPx.y} Q ${wp.x} ${wp.y} ${toPx_.x} ${toPx_.y}`;
  } else {
    // Multiple waypoints - cubic bezier or polyline
    pathD = `M ${fromPx.x} ${fromPx.y}`;
    waypointsPx.forEach((wp) => {
      pathD += ` L ${wp.x} ${wp.y}`;
    });
    pathD += ` L ${toPx_.x} ${toPx_.y}`;
  }

  // Calculate path length for animation
  const pathRef = React.useRef<SVGPathElement>(null);
  const [pathLength, setPathLength] = React.useState(1000);
  
  React.useEffect(() => {
    if (pathRef.current) {
      setPathLength(pathRef.current.getTotalLength());
    }
  }, [pathD]);

  // Dash array for line style
  const getDashArray = () => {
    switch (lineStyle) {
      case "dashed":
        return `${strokeWidth * 4} ${strokeWidth * 2}`;
      case "dotted":
        return `${strokeWidth} ${strokeWidth * 2}`;
      default:
        return "none";
    }
  };

  // Calculate stroke dash offset for animation
  let strokeDashoffset: number;
  switch (direction) {
    case "reverse":
      strokeDashoffset = -pathLength * (1 - progress);
      break;
    case "both":
      // Draw from center outward (not implemented in standard SVG, approximate)
      strokeDashoffset = pathLength * (1 - progress);
      break;
    default:
      strokeDashoffset = pathLength * (1 - progress);
  }

  // Arrow marker
  const arrowId = `arrow-${from.x}-${from.y}-${to.x}-${to.y}`.replace(/\./g, '_');
  const dotId = `dot-${from.x}-${from.y}`.replace(/\./g, '_');
  const diamondId = `diamond-${from.x}-${from.y}`.replace(/\./g, '_');

  // Calculate arrow direction
  const angle = Math.atan2(toPx_.y - fromPx.y, toPx_.x - fromPx.x) * (180 / Math.PI);

  return (
    <AbsoluteFill style={{ zIndex }}>
      <svg width={width} height={height} style={{ overflow: "visible" }}>
        <defs>
          {/* Arrow marker */}
          <marker
            id={arrowId}
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <path d="M0,0 L0,6 L9,3 z" fill={color} />
          </marker>
          
          {/* Dot marker */}
          <marker
            id={dotId}
            markerWidth="6"
            markerHeight="6"
            refX="3"
            refY="3"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <circle cx="3" cy="3" r="2.5" fill={color} />
          </marker>
          
          {/* Diamond marker */}
          <marker
            id={diamondId}
            markerWidth="10"
            markerHeight="10"
            refX="5"
            refY="5"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <polygon points="5,0 10,5 5,10 0,5" fill={color} />
          </marker>

          {/* Glow filter */}
          {glow && (
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation={3 * glowIntensity} result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          )}
        </defs>

        {/* Main line */}
        <path
          ref={pathRef}
          d={pathD}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={lineStyle === "solid" ? pathLength : getDashArray()}
          strokeDashoffset={lineStyle === "solid" ? strokeDashoffset : undefined}
          strokeLinecap="round"
          strokeLinejoin="round"
          markerStart={
            startEnd === "arrow" ? `url(#${arrowId})` :
            startEnd === "dot" ? `url(#${dotId})` :
            startEnd === "diamond" ? `url(#${diamondId})` : undefined
          }
          markerEnd={
            endEnd === "arrow" ? `url(#${arrowId})` :
            endEnd === "dot" ? `url(#${dotId})` :
            endEnd === "diamond" ? `url(#${diamondId})` : undefined
          }
          opacity={progress > 0 ? 1 : 0}
          filter={glow ? "url(#glow)" : undefined}
          style={{
            transition: lineStyle !== "solid" ? "stroke-dashoffset 0.1s" : undefined,
          }}
        />
      </svg>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// CALLOUT LINE - Convenience component for feature callouts
// ─────────────────────────────────────────────────────────────

interface CalloutLineProps {
  /** Feature point location (percentage) */
  featurePoint: Point;
  /** Label location (percentage) */
  labelPoint: Point;
  /** Optional elbow point for L-shaped line */
  elbowPoint?: Point;
  color?: string;
  strokeWidth?: number;
  delay?: number;
  duration?: number;
  /** Dot at feature point */
  showFeatureDot?: boolean;
  featureDotSize?: number;
  zIndex?: number;
}

export const CalloutLine: React.FC<CalloutLineProps> = ({
  featurePoint,
  labelPoint,
  elbowPoint,
  color = "#ffffff",
  strokeWidth = 2,
  delay = 0,
  duration = 30,
  showFeatureDot = true,
  featureDotSize = 8,
  zIndex = 100,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const progress = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: SPRING_CONFIGS.smooth,
  });

  // Convert percentage to pixels
  const fpPx = { x: (featurePoint.x / 100) * width, y: (featurePoint.y / 100) * height };
  const lpPx = { x: (labelPoint.x / 100) * width, y: (labelPoint.y / 100) * height };
  const epPx = elbowPoint 
    ? { x: (elbowPoint.x / 100) * width, y: (elbowPoint.y / 100) * height }
    : null;

  // Build path
  let pathD: string;
  if (epPx) {
    pathD = `M ${fpPx.x} ${fpPx.y} L ${epPx.x} ${epPx.y} L ${lpPx.x} ${lpPx.y}`;
  } else {
    pathD = `M ${fpPx.x} ${fpPx.y} L ${lpPx.x} ${lpPx.y}`;
  }

  // Calculate path length
  const pathRef = React.useRef<SVGPathElement>(null);
  const [pathLength, setPathLength] = React.useState(1000);
  
  React.useEffect(() => {
    if (pathRef.current) {
      setPathLength(pathRef.current.getTotalLength());
    }
  }, [pathD]);

  return (
    <AbsoluteFill style={{ zIndex }}>
      <svg width={width} height={height}>
        {/* Line */}
        <path
          ref={pathRef}
          d={pathD}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={pathLength}
          strokeDashoffset={pathLength * (1 - progress)}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        
        {/* Feature dot */}
        {showFeatureDot && (
          <>
            {/* Outer ring */}
            <circle
              cx={fpPx.x}
              cy={fpPx.y}
              r={featureDotSize * progress}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              opacity={progress}
            />
            {/* Inner dot */}
            <circle
              cx={fpPx.x}
              cy={fpPx.y}
              r={featureDotSize * 0.4 * progress}
              fill={color}
              opacity={progress}
            />
          </>
        )}
      </svg>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// PATH DRAW - Draw any SVG path with animation
// ─────────────────────────────────────────────────────────────

interface PathDrawProps {
  /** SVG path d attribute */
  path: string;
  color?: string;
  strokeWidth?: number;
  fill?: string;
  delay?: number;
  duration?: number;
  easing?: string;
  /** Position offset (percentage) */
  offsetX?: number;
  offsetY?: number;
  /** Scale factor */
  scale?: number;
  zIndex?: number;
}

export const PathDraw: React.FC<PathDrawProps> = ({
  path,
  color = "#ffffff",
  strokeWidth = 2,
  fill = "none",
  delay = 0,
  duration = 60,
  easing,
  offsetX = 0,
  offsetY = 0,
  scale = 1,
  zIndex = 100,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const effectiveFrame = Math.max(0, frame - delay);
  let progress: number;
  
  if (easing) {
    const customEasing = getEasingFromString(easing);
    progress = customEasing 
      ? customEasing(Math.min(1, effectiveFrame / duration))
      : Math.min(1, effectiveFrame / duration);
  } else {
    progress = spring({
      frame: effectiveFrame,
      fps,
      config: SPRING_CONFIGS.smooth,
    });
  }

  const pathRef = React.useRef<SVGPathElement>(null);
  const [pathLength, setPathLength] = React.useState(1000);
  
  React.useEffect(() => {
    if (pathRef.current) {
      setPathLength(pathRef.current.getTotalLength());
    }
  }, [path]);

  const offsetPx = {
    x: (offsetX / 100) * width,
    y: (offsetY / 100) * height,
  };

  return (
    <AbsoluteFill style={{ zIndex }}>
      <svg width={width} height={height}>
        <g transform={`translate(${offsetPx.x}, ${offsetPx.y}) scale(${scale})`}>
          <path
            ref={pathRef}
            d={path}
            stroke={color}
            strokeWidth={strokeWidth}
            fill={fill}
            strokeDasharray={pathLength}
            strokeDashoffset={pathLength * (1 - progress)}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
      </svg>
    </AbsoluteFill>
  );
};
