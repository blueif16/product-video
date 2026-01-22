/**
 * FeatureScene - Feature callout with text and optional visual
 * 
 * Highlights a specific feature with animated text.
 */

import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, Img } from "remotion";
import { z } from "zod";
import { loadFont } from "@remotion/google-fonts/Inter";

import { FadeIn, SlideUp, ScaleIn, HighlightText } from "../components";
import { GradientBackground } from "../components/Background";
import { theme } from "../lib/theme";

const { fontFamily } = loadFont();

// Schema
export const featureSceneSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
  icon: z.string().optional(), // URL to icon/image
  featureNumber: z.number().optional(),
  totalFeatures: z.number().optional(),
  backgroundColor: z.string().optional(),
  accentColor: z.string().optional(),
  layout: z.enum(["center", "left", "right"]).optional(),
});

type FeatureSceneProps = z.infer<typeof featureSceneSchema>;

export const FeatureScene: React.FC<FeatureSceneProps> = ({
  title,
  description,
  icon,
  featureNumber,
  totalFeatures,
  backgroundColor = theme.colors.background,
  accentColor = theme.colors.primary,
  layout = "center",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Exit fade
  const exitOpacity = frame > durationInFrames - 15 
    ? (durationInFrames - frame) / 15 
    : 1;

  const getLayoutStyles = (): React.CSSProperties => {
    switch (layout) {
      case "left":
        return { alignItems: "flex-start", paddingLeft: 120 };
      case "right":
        return { alignItems: "flex-end", paddingRight: 120 };
      default:
        return { alignItems: "center" };
    }
  };

  return (
    <AbsoluteFill style={{ fontFamily }}>
      {/* Background */}
      <GradientBackground colors={[backgroundColor, theme.colors.backgroundDark]} />

      {/* Accent glow */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: layout === "right" ? "70%" : layout === "left" ? "30%" : "50%",
          transform: "translate(-50%, -50%)",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${accentColor}20 0%, transparent 70%)`,
          filter: "blur(60px)",
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          flexDirection: "column",
          gap: 24,
          opacity: exitOpacity,
          padding: theme.spacing.safe,
          ...getLayoutStyles(),
        }}
      >
        {/* Feature number indicator */}
        {featureNumber && totalFeatures && (
          <FadeIn delay={0}>
            <div
              style={{
                fontSize: theme.fontSizes.caption,
                fontWeight: theme.fontWeights.medium,
                color: accentColor,
                letterSpacing: "0.15em",
                textTransform: "uppercase",
              }}
            >
              Feature {featureNumber} of {totalFeatures}
            </div>
          </FadeIn>
        )}

        {/* Icon */}
        {icon && (
          <ScaleIn delay={5}>
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: theme.borderRadius.lg,
                backgroundColor: `${accentColor}20`,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <Img
                src={icon}
                style={{ width: 48, height: 48, objectFit: "contain" }}
              />
            </div>
          </ScaleIn>
        )}

        {/* Title */}
        <SlideUp delay={10}>
          <div
            style={{
              fontSize: theme.fontSizes.title,
              fontWeight: theme.fontWeights.bold,
              color: theme.colors.text,
              textAlign: layout === "center" ? "center" : "left",
              maxWidth: 900,
            }}
          >
            <HighlightText
              text={title}
              highlightColor={accentColor}
              delay={30}
              duration={25}
              type="underline"
            />
          </div>
        </SlideUp>

        {/* Description */}
        {description && (
          <FadeIn delay={40} duration={25}>
            <div
              style={{
                fontSize: theme.fontSizes.heading,
                fontWeight: theme.fontWeights.normal,
                color: theme.colors.textMuted,
                textAlign: layout === "center" ? "center" : "left",
                maxWidth: 700,
                lineHeight: 1.5,
              }}
            >
              {description}
            </div>
          </FadeIn>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
