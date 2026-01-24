/**
 * DeviceFrame Component
 * 
 * Renders screenshots inside realistic device mockups.
 * Critical for Product Hunt quality videos.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, Img, spring, interpolate, staticFile } from "remotion";
import { theme } from "../lib/theme";

type DeviceType = "iphone" | "iphonePro" | "macbook" | "ipad";

interface DeviceFrameProps {
  screenshot: string;
  device?: DeviceType;
  scale?: number;
  animated?: boolean;
  delay?: number;
  shadow?: boolean;
  style?: React.CSSProperties;
}

export const DeviceFrame: React.FC<DeviceFrameProps> = ({
  screenshot,
  device = "iphone",
  scale: baseScale = 1,
  animated = true,
  delay = 0,
  shadow = true,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const deviceConfig = theme.devices[device];

  // Animation
  let animatedScale = 1;
  let opacity = 1;

  if (animated) {
    const progress = spring({
      frame: frame - delay,
      fps,
      config: { damping: 200, stiffness: 80 },
    });
    animatedScale = progress;
    opacity = progress;
  }

  const finalScale = baseScale * animatedScale;

  // Device-specific styling
  const getDeviceStyles = (): React.CSSProperties => {
    const base: React.CSSProperties = {
      position: "relative",
      transform: `scale(${finalScale})`,
      opacity,
      backgroundColor: "#1a1a1a",
      overflow: "hidden",
    };

    switch (device) {
      case "iphone":
      case "iphonePro":
        return {
          ...base,
          width: deviceConfig.width,
          height: deviceConfig.height,
          borderRadius: deviceConfig.borderRadius,
          border: `${deviceConfig.bezelWidth}px solid #1a1a1a`,
          boxShadow: shadow ? theme.shadows.large : "none",
        };

      case "macbook":
        return {
          ...base,
          width: deviceConfig.width,
          height: deviceConfig.height,
          borderRadius: deviceConfig.borderRadius,
          border: `${deviceConfig.bezelWidth}px solid #1a1a1a`,
          borderBottom: `${deviceConfig.chinHeight}px solid #1a1a1a`,
          boxShadow: shadow ? theme.shadows.large : "none",
        };

      case "ipad":
        return {
          ...base,
          width: deviceConfig.width,
          height: deviceConfig.height,
          borderRadius: deviceConfig.borderRadius,
          border: `${deviceConfig.bezelWidth}px solid #1a1a1a`,
          boxShadow: shadow ? theme.shadows.large : "none",
        };

      default:
        return base;
    }
  };

  return (
    <div style={{ ...getDeviceStyles(), ...style }}>
      {/* Notch for iPhone */}
      {(device === "iphone" || device === "iphonePro") && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: "50%",
            transform: "translateX(-50%)",
            width: device === "iphonePro" ? 126 : 150,
            height: device === "iphonePro" ? 37 : 30,
            backgroundColor: "#1a1a1a",
            borderBottomLeftRadius: 20,
            borderBottomRightRadius: 20,
            zIndex: 10,
          }}
        />
      )}

      {/* Screenshot */}
      <Img
        src={
          screenshot.startsWith("http://") || screenshot.startsWith("https://")
            ? screenshot
            : staticFile(screenshot.startsWith("/") ? screenshot.slice(1) : screenshot)
        }
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />

      {/* MacBook chin logo */}
      {device === "macbook" && (
        <div
          style={{
            position: "absolute",
            bottom: -30,
            left: "50%",
            transform: "translateX(-50%)",
            width: 60,
            height: 10,
            backgroundColor: "#333",
            borderRadius: 5,
          }}
        />
      )}
    </div>
  );
};

/**
 * FloatingDevice - Device with floating shadow effect
 */
interface FloatingDeviceProps extends DeviceFrameProps {
  floatIntensity?: number;
}

export const FloatingDevice: React.FC<FloatingDeviceProps> = ({
  floatIntensity = 1,
  ...props
}) => {
  const frame = useCurrentFrame();

  // Subtle floating animation
  const floatY = Math.sin(frame / 30) * 5 * floatIntensity;
  const shadowOffset = 25 + Math.sin(frame / 30) * 3 * floatIntensity;

  return (
    <div
      style={{
        transform: `translateY(${floatY}px)`,
        filter: `drop-shadow(0 ${shadowOffset}px 40px rgba(0, 0, 0, 0.4))`,
      }}
    >
      <DeviceFrame {...props} shadow={false} />
    </div>
  );
};

/**
 * RotatingDevice - 3D rotation effect for device
 */
interface RotatingDeviceProps extends DeviceFrameProps {
  rotateX?: number;
  rotateY?: number;
  perspective?: number;
}

export const RotatingDevice: React.FC<RotatingDeviceProps> = ({
  rotateX = 10,
  rotateY = -15,
  perspective = 1000,
  delay = 0,
  ...props
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
  });

  const currentRotateX = interpolate(progress, [0, 1], [rotateX + 20, rotateX]);
  const currentRotateY = interpolate(progress, [0, 1], [rotateY - 30, rotateY]);

  return (
    <div
      style={{
        perspective,
        transformStyle: "preserve-3d",
      }}
    >
      <div
        style={{
          transform: `rotateX(${currentRotateX}deg) rotateY(${currentRotateY}deg)`,
          transformStyle: "preserve-3d",
        }}
      >
        <DeviceFrame {...props} delay={delay} />
      </div>
    </div>
  );
};
