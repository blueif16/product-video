/**
 * ButtonLayer Component
 * 
 * Animated button/CTA elements for videos.
 * Supports various styles, animations, and pulse effects.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { SPRING_CONFIGS, AnimationFeel, getEasingFromString, getContinuousMotionValues, ContinuousMotionConfig } from "../lib/easing";
import { theme } from "../lib/theme";

// ─────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────

type ButtonVariant = "solid" | "outline" | "ghost" | "gradient";
type ButtonSize = "sm" | "md" | "lg" | "xl";
type EnterAnimation = "fade" | "scale" | "slide_up" | "slide_down" | "pop" | "none";

// ─────────────────────────────────────────────────────────────
// BUTTON LAYER
// ─────────────────────────────────────────────────────────────

interface ButtonLayerProps {
  /** Button text */
  text: string;
  /** Position (percentage coordinates) */
  x?: number;
  y?: number;
  /** Size preset or custom dimensions */
  size?: ButtonSize;
  width?: number;
  height?: number;
  /** Styling */
  variant?: ButtonVariant;
  fillColor?: string;
  textColor?: string;
  borderColor?: string;
  borderWidth?: number;
  borderRadius?: number;
  /** Gradient colors (for gradient variant) */
  gradientColors?: string[];
  gradientAngle?: number;
  /** Typography */
  fontSize?: number;
  fontWeight?: number;
  fontFamily?: string;
  letterSpacing?: string;
  /** Icon (emoji or text) */
  icon?: string;
  iconPosition?: "left" | "right";
  /** Shadow */
  shadow?: boolean;
  shadowColor?: string;
  shadowBlur?: number;
  shadowOffsetY?: number;
  /** Animation */
  enterAnimation?: EnterAnimation;
  delay?: number;
  enterDuration?: number;
  feel?: AnimationFeel;
  easing?: string;
  /** Pulse effect (looping) */
  pulse?: boolean;
  pulseScale?: number;
  pulseDuration?: number;
  /** Continuous motion after entrance */
  continuousMotion?: ContinuousMotionConfig;
  /** Hover-like effect (slight scale) */
  hoverEffect?: boolean;
  /** Z-index */
  zIndex?: number;
}

// Size presets from RAG knowledge
const SIZE_PRESETS: Record<ButtonSize, { width: number; height: number; fontSize: number; padding: number }> = {
  sm: { width: 200, height: 48, fontSize: 16, padding: 16 },
  md: { width: 280, height: 56, fontSize: 18, padding: 24 },
  lg: { width: 360, height: 68, fontSize: 20, padding: 32 },
  xl: { width: 480, height: 80, fontSize: 24, padding: 40 },  // RAG: 300-500px width, 60-80px height
};

export const ButtonLayer: React.FC<ButtonLayerProps> = ({
  text,
  x = 50,
  y = 50,
  size = "lg",
  width: customWidth,
  height: customHeight,
  variant = "solid",
  fillColor = theme.colors.primary,
  textColor = "#ffffff",
  borderColor,
  borderWidth = 2,
  borderRadius = 12,  // RAG: 8-16px
  gradientColors = [theme.colors.primary, theme.colors.accent],
  gradientAngle = 90,
  fontSize: customFontSize,
  fontWeight = 600,
  fontFamily = "Inter, sans-serif",
  letterSpacing,
  icon,
  iconPosition = "left",
  shadow = true,
  shadowColor = "rgba(0, 0, 0, 0.25)",
  shadowBlur = 20,
  shadowOffsetY = 4,
  enterAnimation = "scale",
  delay = 0,
  enterDuration = 15,
  feel = "bouncy",
  easing,
  pulse = false,
  pulseScale = 1.03,  // RAG: 1.0→1.03
  pulseDuration = 45,  // RAG: 30-45 frames
  continuousMotion,
  hoverEffect = false,
  zIndex = 50,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Get size values
  const sizePreset = SIZE_PRESETS[size];
  const buttonWidth = customWidth ?? sizePreset.width;
  const buttonHeight = customHeight ?? sizePreset.height;
  const buttonFontSize = customFontSize ?? sizePreset.fontSize;
  const buttonPadding = sizePreset.padding;

  // Calculate enter animation progress
  const effectiveFrame = Math.max(0, frame - delay);
  let enterProgress: number;
  
  if (easing) {
    const customEasing = getEasingFromString(easing);
    enterProgress = customEasing 
      ? customEasing(Math.min(1, effectiveFrame / enterDuration))
      : Math.min(1, effectiveFrame / enterDuration);
  } else {
    enterProgress = spring({
      frame: effectiveFrame,
      fps,
      config: SPRING_CONFIGS[feel],
    });
  }

  // Calculate enter animation transforms
  let translateY = 0;
  let scale = 1;
  let opacity = 1;

  switch (enterAnimation) {
    case "fade":
      opacity = enterProgress;
      break;
    case "scale":
      scale = interpolate(enterProgress, [0, 1], [0.85, 1]);
      opacity = enterProgress;
      break;
    case "pop":
      scale = enterProgress; // Spring naturally overshoots for bouncy feel
      opacity = enterProgress > 0.1 ? 1 : enterProgress * 10;
      break;
    case "slide_up":
      translateY = interpolate(enterProgress, [0, 1], [50, 0]);
      opacity = enterProgress;
      break;
    case "slide_down":
      translateY = interpolate(enterProgress, [0, 1], [-50, 0]);
      opacity = enterProgress;
      break;
    case "none":
      // Instant appear
      break;
  }

  // Calculate pulse effect (only after entrance complete)
  let pulseScaleFactor = 1;
  if (pulse && enterProgress >= 1) {
    const pulseFrame = effectiveFrame - enterDuration;
    const pulsePhase = (pulseFrame / pulseDuration) * Math.PI * 2;
    const pulseProgress = (Math.sin(pulsePhase) + 1) / 2;
    pulseScaleFactor = 1 + (pulseScale - 1) * pulseProgress;
  }

  // Apply continuous motion
  let motionX = 0, motionY = 0, motionScale = 1, motionOpacity = 1;
  if (continuousMotion && enterProgress >= 1) {
    const motionValues = getContinuousMotionValues(effectiveFrame - enterDuration, continuousMotion);
    motionX = motionValues.x;
    motionY = motionValues.y;
    motionScale = motionValues.scale;
    motionOpacity = motionValues.opacity;
  }

  // Hover effect (subtle scale)
  let hoverScale = 1;
  if (hoverEffect && enterProgress >= 1) {
    hoverScale = 1.02;
  }

  // Final transform values
  const finalScale = scale * pulseScaleFactor * motionScale * hoverScale;
  const finalTranslateY = translateY + motionY;
  const finalTranslateX = motionX;
  const finalOpacity = opacity * motionOpacity;

  // Build background style based on variant
  let background: string;
  let border: string;
  let boxShadowStyle: string = shadow 
    ? `0 ${shadowOffsetY}px ${shadowBlur}px ${shadowColor}` 
    : "none";

  switch (variant) {
    case "gradient":
      background = `linear-gradient(${gradientAngle}deg, ${gradientColors.join(", ")})`;
      border = "none";
      break;
    case "outline":
      background = "transparent";
      border = `${borderWidth}px solid ${borderColor ?? fillColor}`;
      break;
    case "ghost":
      background = `${fillColor}20`; // 12% opacity
      border = "none";
      boxShadowStyle = "none";
      break;
    case "solid":
    default:
      background = fillColor;
      border = "none";
      break;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: `${x}%`,
        top: `${y}%`,
        transform: `translate(-50%, -50%) translateX(${finalTranslateX}px) translateY(${finalTranslateY}px) scale(${finalScale})`,
        opacity: finalOpacity,
        zIndex,
      }}
    >
      <div
        style={{
          width: buttonWidth,
          height: buttonHeight,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          background,
          border,
          borderRadius,
          boxShadow: boxShadowStyle,
          cursor: "pointer",
          transition: "transform 0.1s ease",
        }}
      >
        {icon && iconPosition === "left" && (
          <span style={{ fontSize: buttonFontSize * 1.2 }}>{icon}</span>
        )}
        <span
          style={{
            fontFamily,
            fontSize: buttonFontSize,
            fontWeight,
            color: variant === "outline" ? (borderColor ?? fillColor) : textColor,
            letterSpacing: letterSpacing ?? "0.01em",
            whiteSpace: "nowrap",
          }}
        >
          {text}
        </span>
        {icon && iconPosition === "right" && (
          <span style={{ fontSize: buttonFontSize * 1.2 }}>{icon}</span>
        )}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// PILL BADGE - Small label/tag element
// ─────────────────────────────────────────────────────────────

interface PillBadgeProps {
  text: string;
  x?: number;
  y?: number;
  backgroundColor?: string;
  textColor?: string;
  fontSize?: number;
  fontWeight?: number;
  paddingX?: number;
  paddingY?: number;
  borderRadius?: number;
  delay?: number;
  enterAnimation?: EnterAnimation;
  zIndex?: number;
}

export const PillBadge: React.FC<PillBadgeProps> = ({
  text,
  x = 50,
  y = 50,
  backgroundColor = theme.colors.primary,
  textColor = "#ffffff",
  fontSize = 14,
  fontWeight = 600,
  paddingX = 16,
  paddingY = 8,
  borderRadius = 100,
  delay = 0,
  enterAnimation = "scale",
  zIndex = 50,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: SPRING_CONFIGS.bouncy,
  });

  let scale = 1;
  let opacity = 1;
  let translateY = 0;

  switch (enterAnimation) {
    case "scale":
      scale = progress;
      opacity = progress;
      break;
    case "fade":
      opacity = progress;
      break;
    case "slide_up":
      translateY = interpolate(progress, [0, 1], [20, 0]);
      opacity = progress;
      break;
    default:
      break;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: `${x}%`,
        top: `${y}%`,
        transform: `translate(-50%, -50%) translateY(${translateY}px) scale(${scale})`,
        opacity,
        zIndex,
      }}
    >
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor,
          color: textColor,
          fontSize,
          fontWeight,
          fontFamily: "Inter, sans-serif",
          paddingLeft: paddingX,
          paddingRight: paddingX,
          paddingTop: paddingY,
          paddingBottom: paddingY,
          borderRadius,
          whiteSpace: "nowrap",
        }}
      >
        {text}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// SHAPE LAYER - Basic shapes for backgrounds/decorations
// ─────────────────────────────────────────────────────────────

type ShapeType = "rectangle" | "circle" | "rounded-rectangle" | "pill";

interface ShapeLayerProps {
  shape?: ShapeType;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  fillColor?: string;
  borderColor?: string;
  borderWidth?: number;
  borderRadius?: number;
  opacity?: number;
  /** Gradient fill */
  gradient?: {
    colors: string[];
    angle?: number;
  };
  /** Animation */
  delay?: number;
  enterAnimation?: EnterAnimation;
  /** Shadow */
  shadow?: boolean;
  shadowColor?: string;
  shadowBlur?: number;
  zIndex?: number;
}

export const ShapeLayer: React.FC<ShapeLayerProps> = ({
  shape = "rectangle",
  x = 50,
  y = 50,
  width = 200,
  height = 100,
  fillColor = theme.colors.primary,
  borderColor,
  borderWidth = 0,
  borderRadius: customBorderRadius,
  opacity = 1,
  gradient,
  delay = 0,
  enterAnimation = "fade",
  shadow = false,
  shadowColor = "rgba(0, 0, 0, 0.2)",
  shadowBlur = 20,
  zIndex = 10,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: SPRING_CONFIGS.smooth,
  });

  let animScale = 1;
  let animOpacity = opacity;

  switch (enterAnimation) {
    case "scale":
      animScale = progress;
      animOpacity = opacity * progress;
      break;
    case "fade":
      animOpacity = opacity * progress;
      break;
    default:
      break;
  }

  // Determine border radius based on shape
  let borderRadius: number;
  switch (shape) {
    case "circle":
      borderRadius = Math.max(width, height) / 2;
      break;
    case "pill":
      borderRadius = height / 2;
      break;
    case "rounded-rectangle":
      borderRadius = customBorderRadius ?? 16;
      break;
    default:
      borderRadius = customBorderRadius ?? 0;
  }

  // Background
  const background = gradient
    ? `linear-gradient(${gradient.angle ?? 90}deg, ${gradient.colors.join(", ")})`
    : fillColor;

  return (
    <div
      style={{
        position: "absolute",
        left: `${x}%`,
        top: `${y}%`,
        transform: `translate(-50%, -50%) scale(${animScale})`,
        width,
        height: shape === "circle" ? width : height,
        background,
        border: borderWidth > 0 ? `${borderWidth}px solid ${borderColor ?? fillColor}` : "none",
        borderRadius,
        opacity: animOpacity,
        boxShadow: shadow ? `0 4px ${shadowBlur}px ${shadowColor}` : "none",
        zIndex,
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────
// CARD LAYER - Card with optional stacking effect
// ─────────────────────────────────────────────────────────────

interface CardLayerProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  backgroundColor?: string;
  borderRadius?: number;
  shadow?: boolean;
  /** Stack effect - shows cards behind */
  stack?: boolean;
  stackCount?: number;
  stackOffset?: number;  // RAG: 45-55px offset
  stackRotation?: number;  // Slight rotation for organic feel
  stackScale?: number;  // Smaller scale for back cards
  delay?: number;
  enterAnimation?: EnterAnimation;
  zIndex?: number;
  children?: React.ReactNode;
}

export const CardLayer: React.FC<CardLayerProps> = ({
  x = 50,
  y = 50,
  width = 300,
  height = 200,
  backgroundColor = "#ffffff",
  borderRadius = 16,
  shadow = true,
  stack = false,
  stackCount = 2,
  stackOffset = 15,
  stackRotation = 2,
  stackScale = 0.98,
  delay = 0,
  enterAnimation = "scale",
  zIndex = 20,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: SPRING_CONFIGS.smooth,
  });

  let animScale = 1;
  let animOpacity = 1;
  let translateY = 0;

  switch (enterAnimation) {
    case "scale":
      animScale = interpolate(progress, [0, 1], [0.9, 1]);
      animOpacity = progress;
      break;
    case "fade":
      animOpacity = progress;
      break;
    case "slide_up":
      translateY = interpolate(progress, [0, 1], [30, 0]);
      animOpacity = progress;
      break;
    default:
      break;
  }

  // Render stack cards behind
  const stackCards = stack ? Array.from({ length: stackCount }, (_, i) => {
    const idx = i + 1;
    return (
      <div
        key={`stack-${idx}`}
        style={{
          position: "absolute",
          left: `${x}%`,
          top: `${y}%`,
          transform: `
            translate(-50%, -50%) 
            translateX(${stackOffset * idx}px) 
            translateY(${stackOffset * idx}px) 
            rotate(${stackRotation * idx}deg)
            scale(${Math.pow(stackScale, idx) * animScale})
          `,
          width,
          height,
          backgroundColor,
          borderRadius,
          boxShadow: shadow ? "0 4px 20px rgba(0, 0, 0, 0.1)" : "none",
          opacity: animOpacity * (1 - idx * 0.2),
          zIndex: zIndex - idx,
        }}
      />
    );
  }) : null;

  return (
    <>
      {stackCards}
      <div
        style={{
          position: "absolute",
          left: `${x}%`,
          top: `${y}%`,
          transform: `translate(-50%, -50%) translateY(${translateY}px) scale(${animScale})`,
          width,
          height,
          backgroundColor,
          borderRadius,
          boxShadow: shadow ? "0 8px 30px rgba(0, 0, 0, 0.15)" : "none",
          opacity: animOpacity,
          zIndex,
          overflow: "hidden",
        }}
      >
        {children}
      </div>
    </>
  );
};
