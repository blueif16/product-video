/**
 * Animation Showcase Composition
 * 
 * Demonstrates ALL available text animations for visual testing.
 * Each animation plays for 2 seconds (60 frames at 30fps).
 */

import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";

import { theme } from "../lib/theme";
import { FadeIn, SlideIn, ScaleIn, PopIn } from "../components";
import {
  TypewriterText,
  StaggeredText,
  CountUpText,
  GlitchText,
  HighlightText,
  RevealText,
  WaveText,
} from "../components/AnimatedText";
import {
  OrbsBackground,
  GradientBackground,
  GridBackground,
  NoiseBackground,
  RadialGradientBackground,
} from "../components/Background";

const { fontFamily } = loadFont();

const CLIP_DURATION = 75; // 2.5 seconds per animation

// ─────────────────────────────────────────────────────────────
// Animation Demo Wrapper
// ─────────────────────────────────────────────────────────────

interface DemoProps {
  title: string;
  children: React.ReactNode;
  background?: React.ReactNode;
}

const Demo: React.FC<DemoProps> = ({ title, children, background }) => {
  return (
    <AbsoluteFill>
      {background || (
        <AbsoluteFill style={{ backgroundColor: "#0a0a0f" }} />
      )}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 40,
        }}
      >
        {/* Animation name label */}
        <div
          style={{
            fontFamily,
            fontSize: 24,
            color: "rgba(255, 255, 255, 0.5)",
            position: "absolute",
            top: 40,
            left: 40,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          {title}
        </div>
        
        {/* The animation */}
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Text style for demos
const heroStyle: React.CSSProperties = {
  fontFamily,
  fontSize: 120,
  fontWeight: 800,
  color: "#FFFFFF",
  letterSpacing: "-0.02em",
};

const subtitleStyle: React.CSSProperties = {
  fontFamily,
  fontSize: 48,
  fontWeight: 600,
  color: "#a5b4fc",
};

// ─────────────────────────────────────────────────────────────
// Main Composition
// ─────────────────────────────────────────────────────────────

export const AnimationShowcase: React.FC = () => {
  let offset = 0;
  const clips: Array<{ title: string; content: React.ReactNode; bg?: React.ReactNode }> = [];

  // 1. FADE
  clips.push({
    title: "fade",
    content: (
      <FadeIn duration={20}>
        <div style={heroStyle}>HELLO</div>
      </FadeIn>
    ),
  });

  // 2. SCALE (snappy)
  clips.push({
    title: "scale (snappy)",
    content: (
      <ScaleIn duration={12} startScale={0.85} feel="snappy">
        <div style={heroStyle}>LAUNCH</div>
      </ScaleIn>
    ),
  });

  // 3. POP (bouncy)
  clips.push({
    title: "pop (bouncy)",
    content: (
      <PopIn>
        <div style={heroStyle}>BOUNCE!</div>
      </PopIn>
    ),
    bg: <OrbsBackground />,
  });

  // 4. SLIDE_UP
  clips.push({
    title: "slide_up",
    content: (
      <SlideIn direction="bottom" duration={15}>
        <div style={heroStyle}>RISE UP</div>
      </SlideIn>
    ),
  });

  // 5. SLIDE_DOWN
  clips.push({
    title: "slide_down",
    content: (
      <SlideIn direction="top" duration={15}>
        <div style={heroStyle}>DROP IN</div>
      </SlideIn>
    ),
  });

  // 6. SLIDE_LEFT
  clips.push({
    title: "slide_left",
    content: (
      <SlideIn direction="right" duration={15}>
        <div style={heroStyle}>← SLIDE</div>
      </SlideIn>
    ),
  });

  // 7. SLIDE_RIGHT
  clips.push({
    title: "slide_right",
    content: (
      <SlideIn direction="left" duration={15}>
        <div style={heroStyle}>SLIDE →</div>
      </SlideIn>
    ),
  });

  // 8. TYPEWRITER
  clips.push({
    title: "typewriter",
    content: (
      <TypewriterText
        text="npm run deploy"
        speed={3}
        style={{ ...heroStyle, fontSize: 64, color: "#7ee787" }}
      />
    ),
    bg: <GridBackground color="#0d1117" lineColor="rgba(48,54,61,0.4)" />,
  });

  // 9. STAGGER (words)
  clips.push({
    title: "stagger (by word)",
    content: (
      <StaggeredText
        text="Build faster. Ship smarter."
        by="word"
        staggerDelay={5}
        feel="bouncy"
        style={subtitleStyle}
      />
    ),
    bg: <GradientBackground colors={["#0f172a", "#1e1b4b"]} angle={135} />,
  });

  // 10. STAGGER (characters)
  clips.push({
    title: "stagger (by character)",
    content: (
      <StaggeredText
        text="STREAMLINE"
        by="character"
        staggerDelay={3}
        feel="snappy"
        style={heroStyle}
      />
    ),
  });

  // 11. REVEAL (left)
  clips.push({
    title: "reveal (left)",
    content: (
      <RevealText
        text="PREMIUM"
        direction="left"
        duration={25}
        style={heroStyle}
      />
    ),
    bg: <RadialGradientBackground centerColor="#1e1b4b" edgeColor="#030712" />,
  });

  // 12. REVEAL (bottom)
  clips.push({
    title: "reveal (bottom)",
    content: (
      <RevealText
        text="RISE"
        direction="bottom"
        duration={25}
        style={heroStyle}
      />
    ),
  });

  // 13. COUNTUP
  clips.push({
    title: "countup",
    content: (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
        <CountUpText
          from={0}
          to={1000000}
          duration={50}
          suffix="+"
          style={{ ...heroStyle, fontSize: 140 }}
        />
        <div style={{ ...subtitleStyle, fontSize: 32 }}>Happy Users</div>
      </div>
    ),
    bg: <OrbsBackground orbColors={["#6366f1", "#ec4899", "#8b5cf6"]} />,
  });

  // 14. COUNTUP with decimals
  clips.push({
    title: "countup (percentage)",
    content: (
      <CountUpText
        from={0}
        to={99.9}
        duration={45}
        decimals={1}
        suffix="%"
        style={{ ...heroStyle, fontSize: 160 }}
      />
    ),
  });

  // 15. GLITCH
  clips.push({
    title: "glitch",
    content: (
      <GlitchText
        text="OVERRIDE"
        intensity={1.5}
        duration={25}
        style={{ ...heroStyle, color: "#00ff88" }}
      />
    ),
    bg: <NoiseBackground color="#000000" opacity={0.08} />,
  });

  // 16. HIGHLIGHT (underline)
  clips.push({
    title: "highlight (underline)",
    content: (
      <HighlightText
        text="Important"
        highlightColor="#6366f1"
        type="underline"
        duration={20}
        style={heroStyle}
      />
    ),
  });

  // 17. HIGHLIGHT (background)
  clips.push({
    title: "highlight (background)",
    content: (
      <HighlightText
        text="Featured"
        highlightColor="#ec4899"
        type="background"
        duration={20}
        style={heroStyle}
      />
    ),
    bg: <GradientBackground colors={["#0f0f0f", "#1a1a2e"]} />,
  });

  // 18. WAVE
  clips.push({
    title: "wave",
    content: (
      <WaveText
        text="FLOWING"
        amplitude={12}
        frequency={0.25}
        style={heroStyle}
      />
    ),
    bg: <OrbsBackground orbColors={["#06b6d4", "#3b82f6", "#8b5cf6"]} />,
  });

  // 19. Combined: Scale + Stagger
  clips.push({
    title: "combined (multi-line)",
    content: (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
        <ScaleIn duration={10} feel="snappy">
          <div style={{ ...heroStyle, fontSize: 100 }}>From idea</div>
        </ScaleIn>
        <Sequence from={12}>
          <ScaleIn duration={10} feel="snappy">
            <div style={{ ...heroStyle, fontSize: 100, color: "#a5b4fc" }}>to launch.</div>
          </ScaleIn>
        </Sequence>
      </div>
    ),
    bg: <GradientBackground colors={["#030712", "#0f172a", "#1e1b4b"]} angle={180} />,
  });

  // 20. Feel comparison
  clips.push({
    title: "feel comparison",
    content: (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30 }}>
        <div style={{ display: "flex", gap: 60 }}>
          <div style={{ textAlign: "center" }}>
            <ScaleIn feel="snappy" duration={12}>
              <div style={{ ...subtitleStyle, fontSize: 56 }}>SNAPPY</div>
            </ScaleIn>
          </div>
          <Sequence from={8}>
            <div style={{ textAlign: "center" }}>
              <ScaleIn feel="smooth" duration={20}>
                <div style={{ ...subtitleStyle, fontSize: 56 }}>SMOOTH</div>
              </ScaleIn>
            </div>
          </Sequence>
          <Sequence from={16}>
            <div style={{ textAlign: "center" }}>
              <PopIn>
                <div style={{ ...subtitleStyle, fontSize: 56 }}>BOUNCY</div>
              </PopIn>
            </div>
          </Sequence>
        </div>
      </div>
    ),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {clips.map((clip, i) => (
        <Sequence
          key={i}
          from={i * CLIP_DURATION}
          durationInFrames={CLIP_DURATION}
        >
          <Demo title={clip.title} background={clip.bg}>
            {clip.content}
          </Demo>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

// Export props schema
export const animationShowcaseSchema = {};
