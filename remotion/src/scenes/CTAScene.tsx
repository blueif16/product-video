/**
 * CTAScene - Call to Action ending scene
 * 
 * The closing scene that drives action.
 */

import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, Img, spring, interpolate } from "remotion";
import { z } from "zod";
import { loadFont } from "@remotion/google-fonts/Inter";

import { FadeIn, SlideUp, ScaleIn, PopIn } from "../components";
import { OrbsBackground } from "../components/Background";
import { theme } from "../lib/theme";

const { fontFamily } = loadFont();

// Schema
export const ctaSceneSchema = z.object({
  headline: z.string(),
  subheadline: z.string().optional(),
  ctaText: z.string(),
  ctaUrl: z.string().optional(),
  logo: z.string().optional(),
  backgroundColor: z.string().optional(),
  primaryColor: z.string().optional(),
  showArrow: z.boolean().optional(),
});

type CTASceneProps = z.infer<typeof ctaSceneSchema>;

export const CTAScene: React.FC<CTASceneProps> = ({
  headline,
  subheadline,
  ctaText,
  ctaUrl,
  logo,
  backgroundColor = theme.colors.background,
  primaryColor = theme.colors.primary,
  showArrow = true,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Pulsing animation for CTA button
  const pulse = spring({
    frame: frame - 60,
    fps,
    config: { damping: 5, stiffness: 50 },
  });
  const pulseScale = 1 + Math.sin(frame / 15) * 0.02 * Math.min(pulse, 1);

  // Arrow bounce
  const arrowBounce = Math.sin(frame / 10) * 5;

  return (
    <AbsoluteFill style={{ fontFamily }}>
      {/* Background with orbs */}
      <OrbsBackground
        orbs={[
          { color: primaryColor, size: 800, x: 50, y: 50 },
          { color: theme.colors.accent, size: 500, x: 20, y: 80 },
          { color: theme.colors.accentAlt, size: 400, x: 80, y: 20 },
        ]}
        baseColor={backgroundColor}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 32,
          padding: theme.spacing.safe,
        }}
      >
        {/* Logo */}
        {logo && (
          <ScaleIn delay={0}>
            <Img
              src={logo}
              style={{
                height: 80,
                objectFit: "contain",
                marginBottom: 20,
              }}
            />
          </ScaleIn>
        )}

        {/* Headline */}
        <SlideUp delay={10}>
          <div
            style={{
              fontSize: theme.fontSizes.title,
              fontWeight: theme.fontWeights.bold,
              color: theme.colors.text,
              textAlign: "center",
              maxWidth: 900,
              textShadow: `0 0 60px ${primaryColor}60`,
            }}
          >
            {headline}
          </div>
        </SlideUp>

        {/* Subheadline */}
        {subheadline && (
          <FadeIn delay={30}>
            <div
              style={{
                fontSize: theme.fontSizes.heading,
                fontWeight: theme.fontWeights.normal,
                color: theme.colors.textMuted,
                textAlign: "center",
                maxWidth: 700,
              }}
            >
              {subheadline}
            </div>
          </FadeIn>
        )}

        {/* CTA Button */}
        <PopIn delay={50}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "20px 48px",
              borderRadius: theme.borderRadius.full,
              background: `linear-gradient(135deg, ${primaryColor} 0%, ${theme.colors.accent} 100%)`,
              transform: `scale(${pulseScale})`,
              boxShadow: `0 20px 40px ${primaryColor}40`,
              marginTop: 20,
            }}
          >
            <span
              style={{
                fontSize: theme.fontSizes.heading,
                fontWeight: theme.fontWeights.semibold,
                color: theme.colors.text,
              }}
            >
              {ctaText}
            </span>
            {showArrow && (
              <span
                style={{
                  fontSize: theme.fontSizes.heading,
                  transform: `translateX(${arrowBounce}px)`,
                }}
              >
                →
              </span>
            )}
          </div>
        </PopIn>

        {/* URL display */}
        {ctaUrl && (
          <FadeIn delay={70}>
            <div
              style={{
                fontSize: theme.fontSizes.body,
                fontWeight: theme.fontWeights.medium,
                color: theme.colors.textDark,
                letterSpacing: "0.05em",
                marginTop: 16,
              }}
            >
              {ctaUrl}
            </div>
          </FadeIn>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
