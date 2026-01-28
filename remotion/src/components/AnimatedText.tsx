/**
 * AnimatedText Components - ENHANCED
 * 
 * Full-featured text animation system with:
 * - Custom easing/bezier curves
 * - Irregular stagger arrays
 * - Continuous motion post-entrance
 * - All spring physics presets
 * - Wave animation with full params
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";
import { 
  SPRING_CONFIGS, 
  AnimationFeel, 
  SpringConfig,
  getEasingFromString,
  getStaggerDelay,
  getDurationWithVariance,
  getContinuousMotionValues,
  ContinuousMotionConfig,
} from "../lib/easing";

// ─────────────────────────────────────────────────────────────
// COMMON TYPES
// ─────────────────────────────────────────────────────────────

interface CommonAnimationProps {
  /** Animation feel preset */
  feel?: AnimationFeel;
  /** Custom spring config (overrides feel) */
  springConfig?: SpringConfig;
  /** Custom easing string (e.g., "cubic-bezier(0.34, 1.56, 0.64, 1)" or preset name) */
  easing?: string;
  /** Continuous motion after entrance completes */
  continuousMotion?: ContinuousMotionConfig;
}

// ─────────────────────────────────────────────────────────────
// TYPEWRITER - Characters appear one by one
// ─────────────────────────────────────────────────────────────

interface TypewriterTextProps {
  text: string;
  speed?: number;        // Frames per character
  delay?: number;        // Initial delay in frames
  showCursor?: boolean;
  cursorColor?: string;
  /** NEW: Cursor blink speed in frames */
  cursorBlinkSpeed?: number;
  /** NEW: Delete and retype effect */
  deleteAfter?: number;  // Frames after complete to start deleting
  style?: React.CSSProperties;
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 2,
  delay = 0,
  showCursor = true,
  cursorColor = "#ffffff",
  cursorBlinkSpeed = 30,
  deleteAfter,
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = Math.max(0, frame - delay);
  
  const totalTypeFrames = text.length * speed;
  let visibleChars: number;
  let isDeleting = false;
  
  if (deleteAfter !== undefined) {
    const deleteStart = totalTypeFrames + deleteAfter;
    if (effectiveFrame > deleteStart) {
      isDeleting = true;
      const deleteFrame = effectiveFrame - deleteStart;
      visibleChars = Math.max(0, text.length - Math.floor(deleteFrame / speed));
    } else {
      visibleChars = Math.min(Math.floor(effectiveFrame / speed), text.length);
    }
  } else {
    visibleChars = Math.min(Math.floor(effectiveFrame / speed), text.length);
  }
  
  const isComplete = visibleChars >= text.length && !isDeleting;

  return (
    <span style={{ fontFamily: "monospace", ...style }}>
      {text.slice(0, visibleChars)}
      {showCursor && (!isComplete || isDeleting) && (
        <span
          style={{
            opacity: frame % cursorBlinkSpeed < cursorBlinkSpeed / 2 ? 1 : 0,
            color: cursorColor,
          }}
        >
          |
        </span>
      )}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// STAGGER - Words or characters animate in sequence (ENHANCED)
// ─────────────────────────────────────────────────────────────

interface StaggeredTextProps extends CommonAnimationProps {
  text: string;
  by?: "word" | "character";
  /** Frames between items - can be number OR array for irregular stagger */
  staggerDelay?: number | number[];
  delay?: number;
  /** NEW: Duration variance for organic feel (±frames) */
  durationVariance?: number;
  /** NEW: Per-character animation type */
  staggerAnimation?: "fade" | "slide" | "both" | "scale";
  /** NEW: Slide distance for slide animation */
  slideDistance?: number;
  style?: React.CSSProperties;
}

export const StaggeredText: React.FC<StaggeredTextProps> = ({
  text,
  by = "word",
  staggerDelay = 4,
  delay = 0,
  feel = "bouncy",
  springConfig,
  easing,
  continuousMotion,
  durationVariance,
  staggerAnimation = "both",
  slideDistance = 40,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const items = by === "word" ? text.split(" ") : text.split("");
  const config = springConfig ?? SPRING_CONFIGS[feel];
  
  // Get custom easing function if provided
  const customEasing = easing ? getEasingFromString(easing) : null;

  // Calculate when all items have completed entrance
  const totalItems = items.length;
  const lastItemDelay = getStaggerDelay(totalItems - 1, staggerDelay, durationVariance);
  const entranceComplete = delay + lastItemDelay + 30; // ~30 frames for spring to settle

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: by === "word" ? 12 : 0, ...style }}>
      {items.map((item, i) => {
        const itemDelay = getStaggerDelay(i, staggerDelay, durationVariance);
        const delayedFrame = frame - delay - itemDelay;
        
        // Calculate progress using spring or custom easing
        let itemProgress: number;
        if (customEasing) {
          const linearProgress = Math.min(1, Math.max(0, delayedFrame / 20));
          itemProgress = customEasing(linearProgress);
        } else {
          itemProgress = spring({
            frame: delayedFrame,
            fps,
            config,
          });
        }

        // Base animation values
        let translateY = 0;
        let translateX = 0;
        let scale = 1;
        let opacity = itemProgress;

        // Apply animation type
        switch (staggerAnimation) {
          case "slide":
            translateY = interpolate(itemProgress, [0, 1], [slideDistance, 0]);
            break;
          case "fade":
            // Just opacity, no transform
            break;
          case "scale":
            scale = interpolate(itemProgress, [0, 1], [0.5, 1]);
            break;
          case "both":
          default:
            translateY = interpolate(itemProgress, [0, 1], [slideDistance, 0]);
            opacity = interpolate(itemProgress, [0, 0.5, 1], [0, 0.5, 1]);
            break;
        }

        // Apply continuous motion after entrance
        if (continuousMotion && frame > entranceComplete) {
          const motionValues = getContinuousMotionValues(frame - entranceComplete, continuousMotion);
          translateX += motionValues.x;
          translateY += motionValues.y;
          scale *= motionValues.scale;
          opacity *= motionValues.opacity;
        }

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
              opacity,
              marginRight: by === "character" && item === " " ? "0.3em" : undefined,
            }}
          >
            {item === " " && by === "character" ? "\u00A0" : item}
          </span>
        );
      })}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// COUNTUP - Animates a number counting up
// ─────────────────────────────────────────────────────────────

interface CountUpTextProps extends CommonAnimationProps {
  from?: number;
  to: number;
  duration?: number;      // Duration in frames
  delay?: number;
  prefix?: string;        // e.g., "$"
  suffix?: string;        // e.g., "M+" or "%"
  decimals?: number;      // Decimal places
  separator?: boolean;    // Add thousand separators
  style?: React.CSSProperties;
}

export const CountUpText: React.FC<CountUpTextProps> = ({
  from = 0,
  to,
  duration = 60,
  delay = 0,
  prefix = "",
  suffix = "",
  decimals = 0,
  separator = true,
  easing,
  style,
}) => {
  const frame = useCurrentFrame();
  const customEasing = easing ? getEasingFromString(easing) : null;

  let progress = interpolate(
    frame,
    [delay, delay + duration],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );
  
  // Apply custom easing if provided
  if (customEasing) {
    progress = customEasing(progress);
  }

  const value = from + (to - from) * progress;

  let formattedValue: string;
  if (decimals > 0) {
    formattedValue = value.toFixed(decimals);
  } else {
    const rounded = Math.round(value);
    formattedValue = separator ? rounded.toLocaleString() : String(rounded);
  }

  return (
    <span style={style}>
      {prefix}{formattedValue}{suffix}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// GLITCH - Text with glitch effect then settles
// ─────────────────────────────────────────────────────────────

interface GlitchTextProps extends CommonAnimationProps {
  text: string;
  intensity?: number;     // 0.5 = subtle, 1 = normal, 2 = intense
  delay?: number;         // When glitch starts
  duration?: number;      // How long glitch lasts
  /** NEW: Color shift colors */
  shiftColors?: [string, string];
  /** NEW: Include scanlines */
  scanlines?: boolean;
  style?: React.CSSProperties;
}

export const GlitchText: React.FC<GlitchTextProps> = ({
  text,
  intensity = 1,
  delay = 0,
  duration = 20,
  shiftColors = ["#00ffff", "#ff0040"],
  scanlines = true,
  continuousMotion,
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = frame - delay;

  // Before glitch starts
  if (effectiveFrame < 0) {
    return <span style={{ ...style, opacity: 0 }}>{text}</span>;
  }

  // After glitch ends: show with optional continuous motion
  if (effectiveFrame > duration) {
    let transform = "";
    let opacity = 1;
    
    if (continuousMotion) {
      const motionValues = getContinuousMotionValues(effectiveFrame - duration, continuousMotion);
      transform = `translate(${motionValues.x}px, ${motionValues.y}px) scale(${motionValues.scale})`;
      opacity = motionValues.opacity;
    }
    
    return (
      <span style={{ ...style, transform, opacity, display: "inline-block" }}>
        {text}
      </span>
    );
  }

  // During glitch: apply distortion
  const progress = effectiveFrame / duration;
  const currentIntensity = intensity * (1 - progress * 0.8);
  
  const seed = effectiveFrame * 7.13;
  const offsetX = Math.sin(seed) * 4 * currentIntensity;
  const offsetY = Math.cos(seed * 1.3) * 3 * currentIntensity;
  const skew = Math.sin(seed * 2.1) * 3 * currentIntensity;
  const colorOffset = Math.abs(Math.sin(seed * 0.5)) * 3 * currentIntensity;
  const chromaticOpacity = interpolate(progress, [0, 0.3, 1], [0.6, 0.4, 0]);

  return (
    <span style={{ display: "inline-block", position: "relative", ...style }}>
      {/* Chromatic aberration layers */}
      <span
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          transform: `translateX(${-colorOffset}px)`,
          color: shiftColors[0],
          opacity: chromaticOpacity,
          filter: "blur(0.5px)",
          zIndex: 1,
        }}
        aria-hidden="true"
      >
        {text}
      </span>
      
      <span
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          transform: `translateX(${colorOffset}px)`,
          color: shiftColors[1],
          opacity: chromaticOpacity,
          filter: "blur(0.5px)",
          zIndex: 1,
        }}
        aria-hidden="true"
      >
        {text}
      </span>
      
      {/* Main text */}
      <span
        style={{
          position: "relative",
          display: "inline-block",
          transform: `translate(${offsetX}px, ${offsetY}px) skewX(${skew}deg)`,
          zIndex: 2,
        }}
      >
        {text}
      </span>
      
      {/* Scanlines */}
      {scanlines && currentIntensity > 0.3 && (
        <span
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
            background: `repeating-linear-gradient(
              0deg,
              transparent,
              transparent 2px,
              rgba(0, 0, 0, 0.1) 2px,
              rgba(0, 0, 0, 0.1) 4px
            )`,
            pointerEvents: "none",
            zIndex: 3,
          }}
          aria-hidden="true"
        />
      )}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// HIGHLIGHT - Text with animated highlight/underline
// ─────────────────────────────────────────────────────────────

interface HighlightTextProps extends CommonAnimationProps {
  text: string;
  highlightColor?: string;
  delay?: number;
  duration?: number;
  type?: "underline" | "background" | "box" | "strikethrough";
  /** NEW: Underline thickness */
  thickness?: number;
  /** NEW: Animation direction */
  direction?: "left" | "right" | "center";
  style?: React.CSSProperties;
}

export const HighlightText: React.FC<HighlightTextProps> = ({
  text,
  highlightColor = "#6366f1",
  delay = 0,
  duration = 20,
  type = "underline",
  thickness = 4,
  direction = "left",
  easing,
  style,
}) => {
  const frame = useCurrentFrame();
  const customEasing = easing ? getEasingFromString(easing) : null;

  let progress = interpolate(
    frame,
    [delay, delay + duration],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );
  
  if (customEasing) {
    progress = customEasing(progress);
  }

  // Calculate width and position based on direction
  let width = `${progress * 100}%`;
  let left = "0";
  let right = "auto";
  
  if (direction === "right") {
    left = "auto";
    right = "0";
  } else if (direction === "center") {
    width = `${progress * 100}%`;
    left = `${(1 - progress) * 50}%`;
  }

  if (type === "underline") {
    return (
      <span style={{ position: "relative", display: "inline-block", ...style }}>
        {text}
        <span
          style={{
            position: "absolute",
            bottom: -thickness / 2,
            left,
            right,
            height: thickness,
            width,
            backgroundColor: highlightColor,
            borderRadius: thickness / 2,
          }}
        />
      </span>
    );
  }

  if (type === "strikethrough") {
    return (
      <span style={{ position: "relative", display: "inline-block", ...style }}>
        {text}
        <span
          style={{
            position: "absolute",
            top: "50%",
            left,
            right,
            height: thickness / 2,
            width,
            backgroundColor: highlightColor,
            transform: "translateY(-50%)",
          }}
        />
      </span>
    );
  }

  if (type === "box") {
    return (
      <span
        style={{
          display: "inline-block",
          padding: "0.1em 0.4em",
          border: `${thickness}px solid ${highlightColor}`,
          borderRadius: 4,
          opacity: interpolate(progress, [0, 0.5], [0, 1], { extrapolateRight: "clamp" }),
          transform: `scale(${interpolate(progress, [0, 1], [0.95, 1])})`,
          ...style,
        }}
      >
        {text}
      </span>
    );
  }

  // Background highlight
  return (
    <span
      style={{
        background: `linear-gradient(90deg, ${highlightColor}40 ${progress * 100}%, transparent ${progress * 100}%)`,
        padding: "0.1em 0.3em",
        borderRadius: 4,
        ...style,
      }}
    >
      {text}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// REVEAL - Text reveals with mask animation
// ─────────────────────────────────────────────────────────────

interface RevealTextProps extends CommonAnimationProps {
  text: string;
  direction?: "left" | "right" | "top" | "bottom";
  delay?: number;
  duration?: number;
  /** NEW: Reveal with blur effect */
  blur?: boolean;
  style?: React.CSSProperties;
}

export const RevealText: React.FC<RevealTextProps> = ({
  text,
  direction = "left",
  delay = 0,
  duration = 30,
  easing,
  blur = false,
  continuousMotion,
  style,
}) => {
  const frame = useCurrentFrame();
  const customEasing = easing ? getEasingFromString(easing) : null;

  let progress = interpolate(
    frame,
    [delay, delay + duration],
    [0, 100],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );
  
  if (customEasing) {
    progress = customEasing(progress / 100) * 100;
  }

  const getClipPath = () => {
    switch (direction) {
      case "left":
        return `inset(0 ${100 - progress}% 0 0)`;
      case "right":
        return `inset(0 0 0 ${100 - progress}%)`;
      case "top":
        return `inset(0 0 ${100 - progress}% 0)`;
      case "bottom":
        return `inset(${100 - progress}% 0 0 0)`;
    }
  };

  // Continuous motion after reveal
  let transform = "";
  let opacity = 1;
  if (continuousMotion && progress >= 100) {
    const motionValues = getContinuousMotionValues(frame - delay - duration, continuousMotion);
    transform = `translate(${motionValues.x}px, ${motionValues.y}px) scale(${motionValues.scale})`;
    opacity = motionValues.opacity;
  }

  const blurAmount = blur ? interpolate(progress, [0, 100], [10, 0]) : 0;

  return (
    <span
      style={{
        display: "inline-block",
        clipPath: getClipPath(),
        filter: blur ? `blur(${blurAmount}px)` : undefined,
        transform,
        opacity,
        ...style,
      }}
    >
      {text}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// WAVE - Text with wave animation (NOW FULLY CONFIGURABLE)
// ─────────────────────────────────────────────────────────────

interface WaveTextProps extends CommonAnimationProps {
  text: string;
  /** Wave height in pixels */
  amplitude?: number;
  /** Wave speed (higher = faster) */
  frequency?: number;
  delay?: number;
  /** NEW: Wave spread (character offset multiplier) */
  spread?: number;
  /** NEW: Include scale variation */
  scaleVariation?: boolean;
  /** NEW: Wave direction */
  direction?: "vertical" | "horizontal" | "both";
  style?: React.CSSProperties;
}

export const WaveText: React.FC<WaveTextProps> = ({
  text,
  amplitude = 10,
  frequency = 0.3,
  delay = 0,
  spread = 5,
  scaleVariation = false,
  direction = "vertical",
  continuousMotion,
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = Math.max(0, frame - delay);
  const chars = text.split("");

  return (
    <span style={{ display: "inline-flex", ...style }}>
      {chars.map((char, i) => {
        const phase = (effectiveFrame + i * spread) * frequency;
        
        let translateY = 0;
        let translateX = 0;
        let scale = 1;
        
        if (direction === "vertical" || direction === "both") {
          translateY = Math.sin(phase) * amplitude;
        }
        if (direction === "horizontal" || direction === "both") {
          translateX = Math.cos(phase) * amplitude * 0.5;
        }
        if (scaleVariation) {
          scale = 1 + Math.sin(phase) * 0.1;
        }

        // Add continuous motion if specified
        if (continuousMotion) {
          const motionValues = getContinuousMotionValues(effectiveFrame, continuousMotion);
          translateX += motionValues.x;
          translateY += motionValues.y;
          scale *= motionValues.scale;
        }
        
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
            }}
          >
            {char === " " ? "\u00A0" : char}
          </span>
        );
      })}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// PULSE TEXT - NEW (looping scale animation)
// ─────────────────────────────────────────────────────────────

interface PulseTextProps extends CommonAnimationProps {
  text: string;
  /** Scale range: [minScale, maxScale] */
  scaleRange?: [number, number];
  /** Frames per pulse cycle */
  cycleFrames?: number;
  delay?: number;
  /** Include opacity pulse */
  opacityPulse?: boolean;
  style?: React.CSSProperties;
}

export const PulseText: React.FC<PulseTextProps> = ({
  text,
  scaleRange = [1.0, 1.03],
  cycleFrames = 45,
  delay = 0,
  opacityPulse = false,
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = Math.max(0, frame - delay);
  
  const phase = (effectiveFrame / cycleFrames) * Math.PI * 2;
  const progress = (Math.sin(phase) + 1) / 2; // 0 to 1
  
  const scale = scaleRange[0] + progress * (scaleRange[1] - scaleRange[0]);
  const opacity = opacityPulse ? 0.9 + progress * 0.1 : 1;

  return (
    <span
      style={{
        display: "inline-block",
        transform: `scale(${scale})`,
        opacity,
        ...style,
      }}
    >
      {text}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// SPLIT TEXT - NEW (text splits apart then comes back)
// ─────────────────────────────────────────────────────────────

interface SplitTextProps extends CommonAnimationProps {
  text: string;
  /** Split direction */
  splitDirection?: "horizontal" | "vertical";
  /** Max split distance */
  maxDistance?: number;
  delay?: number;
  duration?: number;
  style?: React.CSSProperties;
}

export const SplitText: React.FC<SplitTextProps> = ({
  text,
  splitDirection = "horizontal",
  maxDistance = 20,
  delay = 0,
  duration = 30,
  feel = "bouncy",
  springConfig,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const config = springConfig ?? SPRING_CONFIGS[feel];
  const progress = spring({
    frame: frame - delay,
    fps,
    config,
  });

  const chars = text.split("");
  const midpoint = chars.length / 2;

  return (
    <span style={{ display: "inline-flex", ...style }}>
      {chars.map((char, i) => {
        const distanceFromMid = i - midpoint;
        const normalizedDist = distanceFromMid / midpoint; // -1 to 1
        
        let translateX = 0;
        let translateY = 0;
        const offset = (1 - progress) * maxDistance * normalizedDist;
        
        if (splitDirection === "horizontal") {
          translateX = offset;
        } else {
          translateY = offset;
        }

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translate(${translateX}px, ${translateY}px)`,
              opacity: progress,
            }}
          >
            {char === " " ? "\u00A0" : char}
          </span>
        );
      })}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// SCRAMBLE TEXT - NEW (random characters resolve to final text)
// ─────────────────────────────────────────────────────────────

interface ScrambleTextProps {
  text: string;
  delay?: number;
  duration?: number;
  /** Characters to use for scrambling */
  charset?: string;
  style?: React.CSSProperties;
}

export const ScrambleText: React.FC<ScrambleTextProps> = ({
  text,
  delay = 0,
  duration = 30,
  charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%",
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = Math.max(0, frame - delay);
  
  const progress = Math.min(1, effectiveFrame / duration);
  const revealedCount = Math.floor(progress * text.length);

  // Generate scrambled text
  const displayText = text.split("").map((char, i) => {
    if (i < revealedCount) {
      return char;
    }
    if (char === " ") {
      return " ";
    }
    // Deterministic pseudo-random based on frame and index
    const seed = (effectiveFrame * 7 + i * 13) % charset.length;
    return charset[seed];
  }).join("");

  return (
    <span style={{ fontFamily: "monospace", ...style }}>
      {displayText}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// BOUNCE IN TEXT - NEW (drops in with bounce)
// ─────────────────────────────────────────────────────────────

interface BounceInTextProps extends CommonAnimationProps {
  text: string;
  delay?: number;
  /** Drop distance */
  dropDistance?: number;
  /** Stagger by word/character */
  by?: "word" | "character" | "none";
  staggerDelay?: number;
  style?: React.CSSProperties;
}

export const BounceInText: React.FC<BounceInTextProps> = ({
  text,
  delay = 0,
  dropDistance = 100,
  by = "none",
  staggerDelay = 3,
  feel = "bouncy",
  springConfig,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const config = springConfig ?? SPRING_CONFIGS[feel];

  if (by === "none") {
    const progress = spring({
      frame: frame - delay,
      fps,
      config,
    });
    
    const translateY = interpolate(progress, [0, 1], [-dropDistance, 0]);
    
    return (
      <span
        style={{
          display: "inline-block",
          transform: `translateY(${translateY}px)`,
          opacity: progress,
          ...style,
        }}
      >
        {text}
      </span>
    );
  }

  const items = by === "word" ? text.split(" ") : text.split("");

  return (
    <span style={{ display: "inline-flex", flexWrap: "wrap", gap: by === "word" ? 12 : 0, ...style }}>
      {items.map((item, i) => {
        const itemDelay = delay + i * staggerDelay;
        const progress = spring({
          frame: frame - itemDelay,
          fps,
          config,
        });
        
        const translateY = interpolate(progress, [0, 1], [-dropDistance, 0]);
        
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translateY(${translateY}px)`,
              opacity: progress,
            }}
          >
            {item === " " && by === "character" ? "\u00A0" : item}
          </span>
        );
      })}
    </span>
  );
};
