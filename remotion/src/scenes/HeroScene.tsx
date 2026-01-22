/**
 * HeroScene - Opening title/tagline scene
 * 
 * The hook that grabs attention in the first 3 seconds.
 */

import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { z } from "zod";
import { loadFont } from "@remotion/google-fonts/Inter";

import { FadeIn, StaggeredText, ScaleIn } from "../components";
import { OrbsBackground } from "../components/Background";
import { theme } from "../lib/theme";

const { fontFamily } = loadFont();

// Schema
export const heroSceneSchema = z.object({
  title: z.string(),
  subtitle: z.string().optional(),
  tagline: z.string().optional(),
  backgroundColor: z.string().optional(),
  primaryColor: z.string().optional(),
  showOrbs: z.boolean().optional(),
});

type HeroSceneProps = z.infer<typeof heroSceneSchema>;

export const HeroScene: React.FC<HeroSceneProps> = ({
  title,
  subtitle,
  tagline,
  backgroundColor = theme.colors.background,
  primaryColor = theme.colors.primary,
  showOrbs = true,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Exit animation
  const exitStart = durationInFrames - 20;
  const isExiting = frame > exitStart;
  const exitOpacity = isExiting 
    ? 1 - (frame - exitStart) / 20 
    : 1;

  return (
    <AbsoluteFill style={{ backgroundColor, fontFamily }}>
      {/* Background */}
      {showOrbs && (
        <OrbsBackground
          orbs={[
            { color: primaryColor, size: 600, x: 20, y: 30 },
            { color: theme.colors.accent, size: 400, x: 80, y: 70 },
            { color: theme.colors.accentAlt, size: 500, x: 60, y: 20 },
          ]}
          baseColor={backgroundColor}
        />
      )}

      {/* Content */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 24,
          opacity: exitOpacity,
          padding: theme.spacing.safe,
        }}
      >
        {/* Tagline (small text above title) */}
        {tagline && (
          <FadeIn delay={0} duration={15}>
            <div
              style={{
                fontSize: theme.fontSizes.body,
                fontWeight: theme.fontWeights.medium,
                color: primaryColor,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
              }}
            >
              {tagline}
            </div>
          </FadeIn>
        )}

        {/* Main title - staggered animation */}
        <StaggeredText
          text={title}
          by="character"
          staggerDelay={3}
          delay={10}
          style={{
            fontSize: theme.fontSizes.hero,
            fontWeight: theme.fontWeights.extrabold,
            color: theme.colors.text,
            letterSpacing: "-0.02em",
            textShadow: `0 0 80px ${primaryColor}80`,
            textAlign: "center",
          }}
        />

        {/* Subtitle */}
        {subtitle && (
          <FadeIn delay={40} duration={20}>
            <div
              style={{
                fontSize: theme.fontSizes.subtitle,
                fontWeight: theme.fontWeights.normal,
                color: theme.colors.textMuted,
                letterSpacing: "0.02em",
                textAlign: "center",
                maxWidth: 800,
              }}
            >
              {subtitle}
            </div>
          </FadeIn>
        )}

        {/* Animated accent line */}
        <ScaleIn delay={60}>
          <div
            style={{
              width: 200,
              height: 4,
              borderRadius: theme.borderRadius.full,
              background: `linear-gradient(90deg, ${primaryColor}, ${theme.colors.accent})`,
              marginTop: 20,
            }}
          />
        </ScaleIn>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
