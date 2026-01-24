/**
 * AnimatedText Components
 * 
 * Collection of text animation patterns for Product Hunt style videos.
 * All animations support customizable spring physics via "feel" parameter.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

type AnimationFeel = "snappy" | "smooth" | "bouncy";

// Spring physics presets
const SPRING_CONFIGS: Record<AnimationFeel, { damping: number; stiffness: number; mass: number }> = {
  snappy: { damping: 25, stiffness: 400, mass: 0.3 },
  smooth: { damping: 20, stiffness: 150, mass: 0.5 },
  bouncy: { damping: 8, stiffness: 200, mass: 0.5 },
};

// ─────────────────────────────────────────────────────────────
// TYPEWRITER - Characters appear one by one
// ─────────────────────────────────────────────────────────────

interface TypewriterTextProps {
  text: string;
  speed?: number;        // Frames per character
  delay?: number;        // Initial delay in frames
  showCursor?: boolean;
  cursorColor?: string;
  style?: React.CSSProperties;
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 2,
  delay = 0,
  showCursor = true,
  cursorColor = "#ffffff",
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = Math.max(0, frame - delay);
  const visibleChars = Math.min(Math.floor(effectiveFrame / speed), text.length);
  const isComplete = visibleChars >= text.length;

  return (
    <span style={{ fontFamily: "monospace", ...style }}>
      {text.slice(0, visibleChars)}
      {showCursor && !isComplete && (
        <span
          style={{
            opacity: frame % 30 < 15 ? 1 : 0,
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
// STAGGER - Words or characters animate in sequence
// ─────────────────────────────────────────────────────────────

interface StaggeredTextProps {
  text: string;
  by?: "word" | "character";
  staggerDelay?: number;   // Frames between items
  delay?: number;          // Initial delay in frames
  feel?: AnimationFeel;    // Spring physics feel
  style?: React.CSSProperties;
}

export const StaggeredText: React.FC<StaggeredTextProps> = ({
  text,
  by = "word",
  staggerDelay = 4,
  delay = 0,
  feel = "bouncy",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const items = by === "word" ? text.split(" ") : text.split("");
  const springConfig = SPRING_CONFIGS[feel];

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: by === "word" ? 12 : 0, ...style }}>
      {items.map((item, i) => {
        const itemProgress = spring({
          frame: frame - delay - i * staggerDelay,
          fps,
          config: springConfig,
        });

        const translateY = interpolate(itemProgress, [0, 1], [40, 0]);
        const opacity = interpolate(itemProgress, [0, 0.5, 1], [0, 0.5, 1]);

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translateY(${translateY}px)`,
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

interface CountUpTextProps {
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
  style,
}) => {
  const frame = useCurrentFrame();

  const value = interpolate(
    frame,
    [delay, delay + duration],
    [from, to],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

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
// GLITCH - Text with glitch effect then settles (FIXED VERSION)
// ─────────────────────────────────────────────────────────────

interface GlitchTextProps {
  text: string;
  intensity?: number;     // 0.5 = subtle, 1 = normal, 2 = intense
  delay?: number;         // When glitch starts
  duration?: number;      // How long glitch lasts
  style?: React.CSSProperties;
}

export const GlitchText: React.FC<GlitchTextProps> = ({
  text,
  intensity = 1,
  delay = 0,
  duration = 20,
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = frame - delay;

  // Before glitch starts
  if (effectiveFrame < 0) {
    return <span style={{ ...style, opacity: 0 }}>{text}</span>;
  }

  // After glitch ends: show normal text
  if (effectiveFrame > duration) {
    return <span style={style}>{text}</span>;
  }

  // During glitch: apply distortion
  const progress = effectiveFrame / duration;
  
  // Reduce intensity as we approach the end (settle effect)
  const currentIntensity = intensity * (1 - progress * 0.8);
  
  // Deterministic pseudo-random based on frame for consistent renders
  const seed = effectiveFrame * 7.13;
  const offsetX = Math.sin(seed) * 4 * currentIntensity;
  const offsetY = Math.cos(seed * 1.3) * 3 * currentIntensity;
  const skew = Math.sin(seed * 2.1) * 3 * currentIntensity;
  
  // Color split offset
  const colorOffset = Math.abs(Math.sin(seed * 0.5)) * 3 * currentIntensity;
  
  // Opacity for chromatic layers (fade in as glitch progresses)
  const chromaticOpacity = interpolate(progress, [0, 0.3, 1], [0.6, 0.4, 0]);

  return (
    <span
      style={{
        display: "inline-block",
        position: "relative",
        ...style,
      }}
    >
      {/* Cyan/blue shadow (offset left) - BEHIND main text */}
      <span
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          transform: `translateX(${-colorOffset}px)`,
          color: "#00ffff",
          opacity: chromaticOpacity,
          filter: "blur(0.5px)",
          zIndex: 1,
        }}
        aria-hidden="true"
      >
        {text}
      </span>
      
      {/* Red/magenta shadow (offset right) - BEHIND main text */}
      <span
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          transform: `translateX(${colorOffset}px)`,
          color: "#ff0040",
          opacity: chromaticOpacity,
          filter: "blur(0.5px)",
          zIndex: 1,
        }}
        aria-hidden="true"
      >
        {text}
      </span>
      
      {/* Main text with position jitter */}
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
      
      {/* Scanline effect during intense glitch */}
      {currentIntensity > 0.3 && (
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

interface HighlightTextProps {
  text: string;
  highlightColor?: string;
  delay?: number;
  duration?: number;      // How long the highlight animation takes
  type?: "underline" | "background";
  style?: React.CSSProperties;
}

export const HighlightText: React.FC<HighlightTextProps> = ({
  text,
  highlightColor = "#6366f1",
  delay = 0,
  duration = 20,
  type = "underline",
  style,
}) => {
  const frame = useCurrentFrame();

  const progress = interpolate(
    frame,
    [delay, delay + duration],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  if (type === "underline") {
    return (
      <span style={{ position: "relative", display: "inline-block", ...style }}>
        {text}
        <span
          style={{
            position: "absolute",
            bottom: -4,
            left: 0,
            height: 4,
            width: `${progress * 100}%`,
            backgroundColor: highlightColor,
            borderRadius: 2,
          }}
        />
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

interface RevealTextProps {
  text: string;
  direction?: "left" | "right" | "top" | "bottom";
  delay?: number;
  duration?: number;
  style?: React.CSSProperties;
}

export const RevealText: React.FC<RevealTextProps> = ({
  text,
  direction = "left",
  delay = 0,
  duration = 30,
  style,
}) => {
  const frame = useCurrentFrame();

  const progress = interpolate(
    frame,
    [delay, delay + duration],
    [0, 100],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

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

  return (
    <span
      style={{
        display: "inline-block",
        clipPath: getClipPath(),
        ...style,
      }}
    >
      {text}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────
// WAVE - Text with wave animation (bonus!)
// ─────────────────────────────────────────────────────────────

interface WaveTextProps {
  text: string;
  amplitude?: number;     // Height of wave in pixels
  frequency?: number;     // Speed of wave
  delay?: number;
  style?: React.CSSProperties;
}

export const WaveText: React.FC<WaveTextProps> = ({
  text,
  amplitude = 10,
  frequency = 0.3,
  delay = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const effectiveFrame = Math.max(0, frame - delay);
  const chars = text.split("");

  return (
    <span style={{ display: "inline-flex", ...style }}>
      {chars.map((char, i) => {
        const offset = Math.sin((effectiveFrame + i * 5) * frequency) * amplitude;
        
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translateY(${offset}px)`,
            }}
          >
            {char === " " ? "\u00A0" : char}
          </span>
        );
      })}
    </span>
  );
};
