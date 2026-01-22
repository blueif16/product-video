/**
 * ScreenshotScene - Display app screenshot with effects
 * 
 * Shows a screenshot with Ken Burns effect, optional device frame,
 * and optional caption overlay.
 */

import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { z } from "zod";
import { loadFont } from "@remotion/google-fonts/Inter";

import { FadeIn, KenBurns, DeviceFrame, FloatingDevice } from "../components";
import { GradientBackground } from "../components/Background";
import { theme } from "../lib/theme";

const { fontFamily } = loadFont();

// Schema
export const screenshotSceneSchema = z.object({
  screenshot: z.string(),
  caption: z.string().optional(),
  subcaption: z.string().optional(),
  device: z.enum(["none", "iphone", "iphonePro", "macbook", "ipad"]).optional(),
  kenBurns: z.enum([
    "none",
    "zoom-in",
    "zoom-out",
    "pan-left",
    "pan-right",
    "zoom-in-pan-left",
    "zoom-in-pan-right",
  ]).optional(),
  floating: z.boolean().optional(),
  backgroundColor: z.string().optional(),
  captionPosition: z.enum(["top", "bottom", "left", "right"]).optional(),
});

type ScreenshotSceneProps = z.infer<typeof screenshotSceneSchema>;

export const ScreenshotScene: React.FC<ScreenshotSceneProps> = ({
  screenshot,
  caption,
  subcaption,
  device = "none",
  kenBurns = "zoom-in",
  floating = false,
  backgroundColor = theme.colors.background,
  captionPosition = "bottom",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Exit fade
  const exitOpacity = frame > durationInFrames - 15 
    ? (durationInFrames - frame) / 15 
    : 1;

  // Layout based on caption position
  const isHorizontalLayout = captionPosition === "left" || captionPosition === "right";

  const renderScreenshot = () => {
    // No device frame - full screen with Ken Burns
    if (device === "none") {
      if (kenBurns === "none") {
        return (
          <AbsoluteFill>
            <img
              src={screenshot}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </AbsoluteFill>
        );
      }
      return <KenBurns src={screenshot} direction={kenBurns} />;
    }

    // With device frame
    const DeviceComponent = floating ? FloatingDevice : DeviceFrame;
    const deviceScale = device === "macbook" ? 0.7 : device === "ipad" ? 0.6 : 0.85;

    return (
      <DeviceComponent
        screenshot={screenshot}
        device={device}
        scale={deviceScale}
        delay={5}
      />
    );
  };

  const renderCaption = () => {
    if (!caption) return null;

    const positionStyles: Record<string, React.CSSProperties> = {
      top: {
        position: "absolute",
        top: theme.spacing.safe,
        left: theme.spacing.safe,
        right: theme.spacing.safe,
        textAlign: "center",
      },
      bottom: {
        position: "absolute",
        bottom: theme.spacing.safe,
        left: theme.spacing.safe,
        right: theme.spacing.safe,
        textAlign: "center",
      },
      left: {
        flex: 1,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        paddingLeft: theme.spacing.safe,
        paddingRight: theme.spacing.lg,
        maxWidth: 500,
      },
      right: {
        flex: 1,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        paddingRight: theme.spacing.safe,
        paddingLeft: theme.spacing.lg,
        maxWidth: 500,
      },
    };

    return (
      <div style={positionStyles[captionPosition]}>
        <FadeIn delay={20}>
          <div
            style={{
              fontSize: theme.fontSizes.heading,
              fontWeight: theme.fontWeights.bold,
              color: theme.colors.text,
              marginBottom: subcaption ? 12 : 0,
            }}
          >
            {caption}
          </div>
        </FadeIn>
        {subcaption && (
          <FadeIn delay={35}>
            <div
              style={{
                fontSize: theme.fontSizes.body,
                fontWeight: theme.fontWeights.normal,
                color: theme.colors.textMuted,
              }}
            >
              {subcaption}
            </div>
          </FadeIn>
        )}
      </div>
    );
  };

  return (
    <AbsoluteFill style={{ fontFamily, opacity: exitOpacity }}>
      {/* Background (only visible with device frame) */}
      {device !== "none" && (
        <GradientBackground 
          colors={[backgroundColor, theme.colors.backgroundDark]} 
        />
      )}

      {/* Main content */}
      {isHorizontalLayout ? (
        // Side-by-side layout
        <AbsoluteFill
          style={{
            flexDirection: captionPosition === "left" ? "row" : "row-reverse",
            display: "flex",
          }}
        >
          {renderCaption()}
          <div
            style={{
              flex: 1,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            {renderScreenshot()}
          </div>
        </AbsoluteFill>
      ) : (
        // Stacked layout
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          {renderScreenshot()}
          {renderCaption()}
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
