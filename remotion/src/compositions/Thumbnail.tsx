/**
 * Thumbnail Composition
 * 
 * For generating video thumbnails and social preview images.
 */

import React from "react";
import { AbsoluteFill, Img } from "remotion";
import { z } from "zod";
import { loadFont } from "@remotion/google-fonts/Inter";

import { OrbsBackground } from "../components/Background";
import { DeviceFrame } from "../components/DeviceFrame";
import { theme } from "../lib/theme";

const { fontFamily } = loadFont();

// Schema
export const thumbnailSchema = z.object({
  title: z.string(),
  subtitle: z.string().optional(),
  screenshot: z.string().optional(),
  logo: z.string().optional(),
  showDevice: z.boolean().optional(),
  device: z.enum(["iphone", "iphonePro", "macbook", "ipad"]).optional(),
  backgroundColor: z.string().optional(),
  primaryColor: z.string().optional(),
  layout: z.enum(["centered", "split"]).optional(),
});

type ThumbnailProps = z.infer<typeof thumbnailSchema>;

export const Thumbnail: React.FC<ThumbnailProps> = ({
  title,
  subtitle,
  screenshot,
  logo,
  showDevice = true,
  device = "iphone",
  backgroundColor = theme.colors.background,
  primaryColor = theme.colors.primary,
  layout = "centered",
}) => {
  if (layout === "split" && screenshot) {
    return (
      <AbsoluteFill style={{ fontFamily }}>
        {/* Background */}
        <OrbsBackground
          orbs={[
            { color: primaryColor, size: 600, x: 25, y: 50 },
            { color: theme.colors.accent, size: 400, x: 75, y: 30 },
          ]}
          baseColor={backgroundColor}
        />

        {/* Split layout */}
        <AbsoluteFill style={{ flexDirection: "row", display: "flex" }}>
          {/* Left side - Text */}
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              padding: theme.spacing.safe,
              gap: 24,
            }}
          >
            {logo && (
              <Img
                src={logo}
                style={{ height: 60, objectFit: "contain", alignSelf: "flex-start" }}
              />
            )}
            <div
              style={{
                fontSize: theme.fontSizes.title,
                fontWeight: theme.fontWeights.bold,
                color: theme.colors.text,
                lineHeight: 1.1,
              }}
            >
              {title}
            </div>
            {subtitle && (
              <div
                style={{
                  fontSize: theme.fontSizes.heading,
                  fontWeight: theme.fontWeights.normal,
                  color: theme.colors.textMuted,
                }}
              >
                {subtitle}
              </div>
            )}
          </div>

          {/* Right side - Device */}
          <div
            style={{
              flex: 1,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            {showDevice ? (
              <DeviceFrame
                screenshot={screenshot}
                device={device}
                scale={device === "macbook" ? 0.6 : 0.75}
                animated={false}
              />
            ) : (
              <Img
                src={screenshot}
                style={{
                  maxWidth: "90%",
                  maxHeight: "90%",
                  objectFit: "contain",
                  borderRadius: theme.borderRadius.lg,
                  boxShadow: theme.shadows.large,
                }}
              />
            )}
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  // Centered layout
  return (
    <AbsoluteFill style={{ fontFamily }}>
      {/* Background */}
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
          <Img
            src={logo}
            style={{ height: 80, objectFit: "contain" }}
          />
        )}

        {/* Screenshot in device */}
        {screenshot && (
          <div style={{ marginBottom: 20 }}>
            {showDevice ? (
              <DeviceFrame
                screenshot={screenshot}
                device={device}
                scale={device === "macbook" ? 0.5 : 0.7}
                animated={false}
              />
            ) : (
              <Img
                src={screenshot}
                style={{
                  maxWidth: 600,
                  maxHeight: 400,
                  objectFit: "contain",
                  borderRadius: theme.borderRadius.lg,
                  boxShadow: theme.shadows.large,
                }}
              />
            )}
          </div>
        )}

        {/* Title */}
        <div
          style={{
            fontSize: screenshot ? theme.fontSizes.subtitle : theme.fontSizes.hero,
            fontWeight: theme.fontWeights.bold,
            color: theme.colors.text,
            textAlign: "center",
            textShadow: `0 0 60px ${primaryColor}60`,
          }}
        >
          {title}
        </div>

        {/* Subtitle */}
        {subtitle && (
          <div
            style={{
              fontSize: theme.fontSizes.heading,
              fontWeight: theme.fontWeights.normal,
              color: theme.colors.textMuted,
              textAlign: "center",
            }}
          >
            {subtitle}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
