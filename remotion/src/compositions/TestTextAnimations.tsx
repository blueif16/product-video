import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
} from "remotion";
import { z } from "zod";
import { loadFont } from "@remotion/google-fonts/Inter";

// Load Inter font
const { fontFamily } = loadFont();

// Schema for props
export const testTextAnimationsSchema = z.object({
  title: z.string(),
  subtitle: z.string(),
  backgroundColor: z.string(),
  primaryColor: z.string(),
});

type TestTextAnimationsProps = z.infer<typeof testTextAnimationsSchema>;

// ─────────────────────────────────────────────────────────────
// Reusable Animation Components
// ─────────────────────────────────────────────────────────────

const FadeIn: React.FC<{
  children: React.ReactNode;
  delay?: number;
  duration?: number;
}> = ({ children, delay = 0, duration = 20 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  return <div style={{ opacity }}>{children}</div>;
};

const SlideUp: React.FC<{
  children: React.ReactNode;
  delay?: number;
}> = ({ children, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200, stiffness: 100 },
  });

  const translateY = interpolate(progress, [0, 1], [50, 0]);
  const opacity = interpolate(progress, [0, 1], [0, 1]);

  return (
    <div style={{ transform: `translateY(${translateY}px)`, opacity }}>
      {children}
    </div>
  );
};

const ScaleIn: React.FC<{
  children: React.ReactNode;
  delay?: number;
}> = ({ children, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame: frame - delay,
    fps,
    config: { damping: 12, stiffness: 100, mass: 0.5 },
  });

  return (
    <div
      style={{
        transform: `scale(${scale})`,
        transformOrigin: "center",
      }}
    >
      {children}
    </div>
  );
};

// Staggered character animation
const StaggeredText: React.FC<{
  text: string;
  staggerDelay?: number;
  startDelay?: number;
  style?: React.CSSProperties;
}> = ({ text, staggerDelay = 3, startDelay = 0, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const characters = text.split("");

  return (
    <div style={{ display: "flex", justifyContent: "center", ...style }}>
      {characters.map((char, i) => {
        const charProgress = spring({
          frame: frame - startDelay - i * staggerDelay,
          fps,
          config: { damping: 15, stiffness: 150 },
        });

        const translateY = interpolate(charProgress, [0, 1], [40, 0]);
        const opacity = interpolate(charProgress, [0, 0.5, 1], [0, 0.5, 1]);

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translateY(${translateY}px)`,
              opacity,
              marginRight: char === " " ? "0.3em" : "0.02em",
            }}
          >
            {char === " " ? "\u00A0" : char}
          </span>
        );
      })}
    </div>
  );
};

// Glowing orb background effect
const GlowingOrb: React.FC<{
  color: string;
  size: number;
  x: number;
  y: number;
  delay?: number;
}> = ({ color, size, x, y, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame: frame - delay,
    fps,
    config: { damping: 20, stiffness: 50 },
  });

  const pulse = interpolate(
    Math.sin((frame + delay * 10) / 20),
    [-1, 1],
    [0.9, 1.1]
  );

  return (
    <div
      style={{
        position: "absolute",
        left: `${x}%`,
        top: `${y}%`,
        width: size,
        height: size,
        borderRadius: "50%",
        background: `radial-gradient(circle, ${color}40 0%, transparent 70%)`,
        transform: `translate(-50%, -50%) scale(${scale * pulse})`,
        filter: "blur(40px)",
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────
// Main Composition
// ─────────────────────────────────────────────────────────────

export const TestTextAnimations: React.FC<TestTextAnimationsProps> = ({
  title,
  subtitle,
  backgroundColor,
  primaryColor,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Exit animation (last 20 frames)
  const exitProgress = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const exitOpacity = 1 - exitProgress;
  const exitScale = interpolate(exitProgress, [0, 1], [1, 0.9]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor,
        fontFamily,
        overflow: "hidden",
      }}
    >
      {/* Animated background orbs */}
      <GlowingOrb color={primaryColor} size={600} x={20} y={30} delay={0} />
      <GlowingOrb color="#ec4899" size={400} x={80} y={70} delay={10} />
      <GlowingOrb color="#06b6d4" size={500} x={60} y={20} delay={20} />

      {/* Content with exit animation */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          opacity: exitOpacity,
          transform: `scale(${exitScale})`,
        }}
      >
        {/* Main title - staggered character animation */}
        <Sequence from={10}>
          <StaggeredText
            text={title}
            staggerDelay={4}
            style={{
              fontSize: 120,
              fontWeight: 800,
              color: "#ffffff",
              letterSpacing: "-0.02em",
              textShadow: `0 0 80px ${primaryColor}80`,
            }}
          />
        </Sequence>

        {/* Subtitle - slide up */}
        <Sequence from={40}>
          <div style={{ marginTop: 30 }}>
            <SlideUp>
              <div
                style={{
                  fontSize: 36,
                  fontWeight: 400,
                  color: "#94a3b8",
                  letterSpacing: "0.05em",
                }}
              >
                {subtitle}
              </div>
            </SlideUp>
          </div>
        </Sequence>

        {/* Animated underline */}
        <Sequence from={60}>
          <div style={{ marginTop: 40 }}>
            <ScaleIn>
              <div
                style={{
                  width: 200,
                  height: 4,
                  borderRadius: 2,
                  background: `linear-gradient(90deg, ${primaryColor}, #ec4899)`,
                }}
              />
            </ScaleIn>
          </div>
        </Sequence>

        {/* "Ready to render" badge */}
        <Sequence from={80}>
          <div style={{ marginTop: 60 }}>
            <FadeIn duration={30}>
              <div
                style={{
                  padding: "12px 24px",
                  borderRadius: 100,
                  background: `${primaryColor}20`,
                  border: `1px solid ${primaryColor}50`,
                  color: primaryColor,
                  fontSize: 18,
                  fontWeight: 500,
                }}
              >
                ✓ Remotion is working
              </div>
            </FadeIn>
          </div>
        </Sequence>
      </AbsoluteFill>

      {/* Frame counter (for debugging) */}
      <div
        style={{
          position: "absolute",
          bottom: 30,
          right: 30,
          color: "#475569",
          fontSize: 14,
          fontFamily: "monospace",
        }}
      >
        Frame {frame}/{durationInFrames} • {fps}fps
      </div>
    </AbsoluteFill>
  );
};
