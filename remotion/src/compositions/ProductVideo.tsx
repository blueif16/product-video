/**
 * ProductVideo Composition
 * 
 * Main composition for rendering product videos from VideoSpec JSON.
 * FULL ANIMATION SUPPORT - 14 text animations, 6 backgrounds, 10 transforms.
 * 
 * Animation Philosophy:
 * - snappy: Fast, no bounce (corporate, professional)
 * - smooth: Medium speed, gentle ease (elegant, premium)
 * - bouncy: Overshoot and settle (playful, energetic)
 */

import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
  Img,
  interpolate,
  spring,
  Audio,
  staticFile,
  Easing,
} from "remotion";
import { z } from "zod";
import { loadFont } from "@remotion/google-fonts/Inter";

import { theme } from "../lib/theme";
import { KenBurns, FocusZoom, ParallaxImage } from "../components/KenBurns";
import { DeviceFrame } from "../components/DeviceFrame";
import {
  TypewriterText,
  StaggeredText,
  RevealText,
  CountUpText,
  GlitchText,
  HighlightText,
} from "../components/AnimatedText";
import { FadeIn, SlideIn, ScaleIn, PopIn } from "../components";
import {
  OrbsBackground,
  GradientBackground,
  GridBackground,
  NoiseBackground,
  RadialGradientBackground,
} from "../components/Background";

const { fontFamily } = loadFont();

// ─────────────────────────────────────────────────────────────
// Spring Physics Presets
// ─────────────────────────────────────────────────────────────

const SPRING_CONFIGS = {
  snappy: { damping: 25, stiffness: 400, mass: 0.3 },
  smooth: { damping: 20, stiffness: 150, mass: 0.5 },
  bouncy: { damping: 8, stiffness: 200, mass: 0.5 },
} as const;

type AnimationFeel = keyof typeof SPRING_CONFIGS;

// ─────────────────────────────────────────────────────────────
// Schema - Matches VideoSpec from Python editor
// ─────────────────────────────────────────────────────────────

const transformSchema = z.object({
  type: z.enum([
    "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down",
    "static", "focus", "ken_burns", "parallax"
  ]),
  startScale: z.number().optional(),
  endScale: z.number().optional(),
  focusX: z.number().optional(),
  focusY: z.number().optional(),
  intensity: z.number().optional(),
  parallaxSpeed: z.number().optional(),
  parallaxDirection: z.enum(["horizontal", "vertical"]).optional(),
});

const opacitySchema = z.object({
  start: z.number(),
  end: z.number(),
});

const positionSchema = z.object({
  preset: z.enum([
    "center", "top", "bottom", "left", "right",
    "top_left", "top_right", "bottom_left", "bottom_right",
    "top-left", "top-right", "bottom-left", "bottom-right"  // Legacy support
  ]).optional(),
  x: z.number().optional(),
  y: z.number().optional(),
});

const textAnimationSchema = z.object({
  enter: z.enum([
    "fade", "scale", "pop", "slide_up", "slide_down", "slide_left", "slide_right",
    "typewriter", "stagger", "reveal", "glitch", "highlight", "countup", "none"
  ]),
  exit: z.enum(["fade", "slide_up", "slide_down", "scale", "none"]).optional(),
  enterDuration: z.number().optional(),
  exitDuration: z.number().optional(),
  feel: z.enum(["snappy", "smooth", "bouncy"]).optional(),
  // Typewriter
  typewriterSpeed: z.number().optional(),
  showCursor: z.boolean().optional(),
  // Stagger
  staggerBy: z.enum(["word", "character"]).optional(),
  staggerDelay: z.number().optional(),
  // Reveal
  revealDirection: z.enum(["left", "right", "top", "bottom"]).optional(),
  // Highlight
  highlightType: z.enum(["underline", "background"]).optional(),
  // Countup
  countupFrom: z.number().optional(),
  countupDecimals: z.number().optional(),
  countupPrefix: z.string().optional(),
  countupSuffix: z.string().optional(),
  // Glitch
  glitchIntensity: z.number().optional(),
});

const textStyleSchema = z.object({
  fontSize: z.number(),
  fontWeight: z.number(),
  color: z.string(),
  textAlign: z.enum(["left", "center", "right"]).optional(),
  letterSpacing: z.string().optional(),
  textShadow: z.string().optional(),
  lineHeight: z.number().optional(),
  maxWidth: z.number().optional(),
  highlightColor: z.string().optional(),
});

// Layer schemas
const imageLayerSchema = z.object({
  type: z.literal("image"),
  src: z.string(),
  zIndex: z.number(),
  transform: transformSchema.optional(),
  opacity: opacitySchema.optional(),
  device: z.enum(["none", "iphone", "iphonePro", "macbook", "ipad"]).optional(),
  startFrame: z.number().optional(),
  durationFrames: z.number().optional(),
});

const generatedImageLayerSchema = z.object({
  type: z.literal("generated_image"),
  src: z.string(),
  zIndex: z.number(),
  transform: transformSchema.optional(),
  opacity: opacitySchema.optional(),
  generatedAssetId: z.string().optional(),
});

const textLayerSchema = z.object({
  type: z.literal("text"),
  content: z.string(),
  zIndex: z.number(),
  style: textStyleSchema,
  animation: textAnimationSchema,
  position: positionSchema,
  startFrame: z.number().optional(),
  durationFrames: z.number().optional(),
});

const gradientSpecSchema = z.object({
  colors: z.array(z.string()),
  angle: z.number().optional(),
  animate: z.boolean().optional(),
});

const backgroundLayerSchema = z.object({
  type: z.literal("background"),
  zIndex: z.number(),
  color: z.string().optional(),
  gradient: gradientSpecSchema.optional(),
  // Orbs
  orbs: z.boolean().optional(),
  orbColors: z.array(z.string()).optional(),
  // Grid
  grid: z.boolean().optional(),
  gridSize: z.number().optional(),
  gridColor: z.string().optional(),
  gridAnimated: z.boolean().optional(),
  // Noise
  noise: z.boolean().optional(),
  noiseOpacity: z.number().optional(),
  // Radial
  radial: z.boolean().optional(),
  radialCenterX: z.number().optional(),
  radialCenterY: z.number().optional(),
  radialCenterColor: z.string().optional(),
  radialEdgeColor: z.string().optional(),
});

const layerSchema = z.discriminatedUnion("type", [
  imageLayerSchema,
  generatedImageLayerSchema,
  textLayerSchema,
  backgroundLayerSchema,
]);

const transitionSchema = z.object({
  type: z.enum(["fade", "slide", "slide_left", "slide_right", "slide_up", "slide_down", "wipe", "none"]),
  durationFrames: z.number(),
});

const clipSchema = z.object({
  id: z.string(),
  startFrame: z.number(),
  durationFrames: z.number(),
  layers: z.array(layerSchema),
  enterTransition: transitionSchema.optional(),
  exitTransition: transitionSchema.optional(),
  backgroundColor: z.string().optional(),
});

const audioSchema = z.object({
  src: z.string(),
  volume: z.number().optional(),
  startFrame: z.number().optional(),
  fadeIn: z.number().optional(),
  fadeOut: z.number().optional(),
  loop: z.boolean().optional(),
});

export const productVideoSchema = z.object({
  meta: z.object({
    title: z.string(),
    durationFrames: z.number(),
    fps: z.number(),
    resolution: z.object({
      width: z.number(),
      height: z.number(),
    }),
  }),
  clips: z.array(clipSchema),
  audio: audioSchema.optional(),
  backgroundColor: z.string().optional(),
});

type ProductVideoProps = z.infer<typeof productVideoSchema>;
type Layer = z.infer<typeof layerSchema>;
type Clip = z.infer<typeof clipSchema>;

// ─────────────────────────────────────────────────────────────
// Background Layer Renderer (6 types)
// ─────────────────────────────────────────────────────────────

const BackgroundLayerRenderer: React.FC<{
  layer: z.infer<typeof backgroundLayerSchema>;
}> = ({ layer }) => {
  const baseColor = layer.color || theme.colors.backgroundDark;

  // Priority: radial > orbs > gradient > grid/noise > solid
  
  // Radial gradient spotlight
  if (layer.radial) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex }}>
        <RadialGradientBackground
          centerColor={layer.radialCenterColor || theme.colors.backgroundLight}
          edgeColor={layer.radialEdgeColor || theme.colors.backgroundDark}
          centerX={layer.radialCenterX ?? 50}
          centerY={layer.radialCenterY ?? 50}
        />
      </AbsoluteFill>
    );
  }

  // Animated glowing orbs
  if (layer.orbs) {
    const colors = layer.orbColors || [theme.colors.primary, theme.colors.accent, theme.colors.accentAlt];
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex }}>
        <OrbsBackground
          orbs={colors.map((color, i) => ({
            color,
            size: 400 + i * 100,
            x: 20 + i * 30,
            y: 20 + i * 25,
          }))}
          baseColor={baseColor}
        />
      </AbsoluteFill>
    );
  }

  // Linear gradient
  if (layer.gradient) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex }}>
        <GradientBackground
          colors={layer.gradient.colors}
          angle={layer.gradient.angle ?? 180}
          animate={layer.gradient.animate ?? false}
        />
      </AbsoluteFill>
    );
  }

  // Grid pattern (can combine with solid color)
  if (layer.grid) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex }}>
        <GridBackground
          color={baseColor}
          lineColor={layer.gridColor || theme.colors.overlayLight}
          gridSize={layer.gridSize ?? 40}
          animated={layer.gridAnimated ?? false}
        />
      </AbsoluteFill>
    );
  }

  // Noise texture (can combine with solid color)
  if (layer.noise) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex }}>
        <NoiseBackground
          color={baseColor}
          opacity={layer.noiseOpacity ?? 0.05}
        />
      </AbsoluteFill>
    );
  }

  // Solid color fallback
  return (
    <AbsoluteFill
      style={{
        zIndex: layer.zIndex,
        backgroundColor: baseColor,
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────
// Image Layer Renderer (10 transforms)
// ─────────────────────────────────────────────────────────────

const ImageLayerRenderer: React.FC<{
  layer: z.infer<typeof imageLayerSchema> | z.infer<typeof generatedImageLayerSchema>;
  clipFrame: number;
  clipDuration: number;
}> = ({ layer, clipFrame, clipDuration }) => {
  const progress = clipDuration > 0 ? clipFrame / clipDuration : 0;

  // Skip if src is invalid
  if (!layer.src || layer.src.startsWith("none://") || layer.src === "") {
    return null;
  }

  // Handle relative paths (from remotion/public/) with staticFile()
  let imageSrc = layer.src;
  if (!layer.src.startsWith("http://") && !layer.src.startsWith("https://")) {
    // Strip leading slash if present, staticFile() expects relative paths
    const cleanPath = layer.src.startsWith("/") ? layer.src.slice(1) : layer.src;
    imageSrc = staticFile(cleanPath);
  }

  // Opacity animation (for crossfades)
  let opacity = 1;
  if (layer.opacity) {
    opacity = interpolate(progress, [0, 1], [layer.opacity.start, layer.opacity.end], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  }

  // Device frame handling
  const device = "device" in layer ? layer.device : undefined;
  if (device && device !== "none") {
    // Clean path for DeviceFrame (strip leading slash for staticFile)
    const cleanScreenshotPath = layer.src.startsWith("/") ? layer.src.slice(1) : layer.src;
    return (
      <AbsoluteFill
        style={{
          zIndex: layer.zIndex,
          justifyContent: "center",
          alignItems: "center",
          opacity,
        }}
      >
        <DeviceFrame
          screenshot={cleanScreenshotPath}
          device={device}
          scale={device === "macbook" ? 0.6 : device === "ipad" ? 0.55 : 0.8}
          animated={false}
        />
      </AbsoluteFill>
    );
  }

  // Transform handling
  if (layer.transform) {
    const t = layer.transform;
    const intensity = t.intensity ?? 1;

    // Parallax effect
    if (t.type === "parallax") {
      return (
        <AbsoluteFill style={{ zIndex: layer.zIndex, opacity }}>
          <ParallaxImage
            src={layer.src}
            speed={t.parallaxSpeed ?? 0.5}
            direction={t.parallaxDirection ?? "vertical"}
          />
        </AbsoluteFill>
      );
    }

    // Focus zoom on specific point
    if (t.type === "focus" && t.focusX !== undefined && t.focusY !== undefined) {
      return (
        <AbsoluteFill style={{ zIndex: layer.zIndex, opacity }}>
          <FocusZoom
            src={layer.src}
            focusX={t.focusX}
            focusY={t.focusY}
            startScale={t.startScale ?? 1}
            endScale={t.endScale ?? 1.3}
          />
        </AbsoluteFill>
      );
    }

    // Ken Burns and other directional movements
    if (t.type !== "static") {
      const kenBurnsDirection = t.type === "ken_burns"
        ? "zoom-in"
        : t.type.replace("_", "-") as any;
      return (
        <AbsoluteFill style={{ zIndex: layer.zIndex, opacity }}>
          <KenBurns
            src={layer.src}
            direction={kenBurnsDirection}
            intensity={intensity}
          />
        </AbsoluteFill>
      );
    }
  }

  // Static image
  return (
    <AbsoluteFill style={{ zIndex: layer.zIndex, opacity }}>
      <Img
        src={layer.src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// Text Layer Renderer (14 enter animations)
// ─────────────────────────────────────────────────────────────

const TextLayerRenderer: React.FC<{
  layer: z.infer<typeof textLayerSchema>;
  clipFrame: number;
  clipDuration: number;
  fps: number;
}> = ({ layer, clipFrame, clipDuration, fps }) => {
  const { content, style, animation, position, startFrame = 0, durationFrames } = layer;

  // Check visibility
  const localFrame = clipFrame - startFrame;
  const textDuration = durationFrames ?? clipDuration - startFrame;

  if (localFrame < 0) return null;
  if (durationFrames && localFrame > durationFrames) return null;

  // Animation parameters
  const enterDuration = animation.enterDuration ?? 10;
  const exitDuration = animation.exitDuration ?? 8;
  const feel: AnimationFeel = animation.feel ?? "snappy";
  const springConfig = SPRING_CONFIGS[feel];

  // Exit animation progress
  const exitStart = textDuration - exitDuration;
  const isExiting = localFrame > exitStart && animation.exit !== "none";

  // Position styles
  const positionStyles: React.CSSProperties = {
    position: "absolute",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: theme.spacing.safe,
  };

  // Normalize preset (support both underscore and hyphen)
  const rawPreset = position.preset ?? "center";
  const preset = rawPreset.replace(/-/g, "_");

  switch (preset) {
    case "center":
      positionStyles.inset = 0;
      break;
    case "top":
      positionStyles.top = 0;
      positionStyles.left = 0;
      positionStyles.right = 0;
      positionStyles.height = "auto";
      positionStyles.paddingTop = theme.spacing.safe * 2;
      break;
    case "bottom":
      positionStyles.bottom = 0;
      positionStyles.left = 0;
      positionStyles.right = 0;
      positionStyles.height = "auto";
      positionStyles.paddingBottom = theme.spacing.safe * 2;
      break;
    case "left":
      positionStyles.left = 0;
      positionStyles.top = 0;
      positionStyles.bottom = 0;
      positionStyles.width = "50%";
      positionStyles.justifyContent = "flex-start";
      break;
    case "right":
      positionStyles.right = 0;
      positionStyles.top = 0;
      positionStyles.bottom = 0;
      positionStyles.width = "50%";
      positionStyles.justifyContent = "flex-end";
      break;
    case "top_left":
      positionStyles.top = 0;
      positionStyles.left = 0;
      positionStyles.justifyContent = "flex-start";
      positionStyles.alignItems = "flex-start";
      break;
    case "top_right":
      positionStyles.top = 0;
      positionStyles.right = 0;
      positionStyles.justifyContent = "flex-end";
      positionStyles.alignItems = "flex-start";
      break;
    case "bottom_left":
      positionStyles.bottom = 0;
      positionStyles.left = 0;
      positionStyles.justifyContent = "flex-start";
      positionStyles.alignItems = "flex-end";
      break;
    case "bottom_right":
      positionStyles.bottom = 0;
      positionStyles.right = 0;
      positionStyles.justifyContent = "flex-end";
      positionStyles.alignItems = "flex-end";
      break;
  }

  // Custom position overrides
  if (position.x !== undefined || position.y !== undefined) {
    positionStyles.inset = undefined;

    if (position.x !== undefined && position.y !== undefined) {
      // Both x and y: absolute positioning with centering
      positionStyles.left = `${position.x}%`;
      positionStyles.top = `${position.y}%`;
      positionStyles.transform = "translate(-50%, -50%)";
    } else if (position.y !== undefined) {
      // Only y: keep horizontal centering, adjust vertical position
      positionStyles.left = 0;
      positionStyles.right = 0;
      positionStyles.top = `${position.y}%`;
      positionStyles.transform = "translateY(-50%)";
    } else if (position.x !== undefined) {
      // Only x: keep vertical centering, adjust horizontal position
      positionStyles.top = 0;
      positionStyles.bottom = 0;
      positionStyles.left = `${position.x}%`;
      positionStyles.transform = "translateX(-50%)";
    }

    positionStyles.justifyContent = "center";
    positionStyles.alignItems = "center";
  }

  // Text styling
  const textStyles: React.CSSProperties = {
    fontFamily,
    fontSize: style.fontSize,
    fontWeight: style.fontWeight,
    color: style.color,
    textAlign: style.textAlign ?? "center",
    letterSpacing: style.letterSpacing,
    textShadow: style.textShadow,
    lineHeight: style.lineHeight ?? 1.2,
    maxWidth: style.maxWidth,
  };

  // Exit animation wrapper
  const wrapWithExit = (children: React.ReactNode) => {
    if (!animation.exit || animation.exit === "none" || !isExiting) {
      return children;
    }

    const exitProgress = (localFrame - exitStart) / exitDuration;

    switch (animation.exit) {
      case "fade":
        return (
          <div style={{ opacity: interpolate(exitProgress, [0, 1], [1, 0], { extrapolateRight: "clamp" }) }}>
            {children}
          </div>
        );
      case "slide_down":
        return (
          <div style={{
            transform: `translateY(${interpolate(exitProgress, [0, 1], [0, 50])}px)`,
            opacity: interpolate(exitProgress, [0, 1], [1, 0], { extrapolateRight: "clamp" })
          }}>
            {children}
          </div>
        );
      case "slide_up":
        return (
          <div style={{
            transform: `translateY(${interpolate(exitProgress, [0, 1], [0, -50])}px)`,
            opacity: interpolate(exitProgress, [0, 1], [1, 0], { extrapolateRight: "clamp" })
          }}>
            {children}
          </div>
        );
      case "scale":
        return (
          <div style={{
            transform: `scale(${interpolate(exitProgress, [0, 1], [1, 0.85])})`,
            opacity: interpolate(exitProgress, [0, 1], [1, 0], { extrapolateRight: "clamp" })
          }}>
            {children}
          </div>
        );
      default:
        return children;
    }
  };

  // Render based on animation type
  const renderAnimatedText = () => {
    switch (animation.enter) {
      // ─────────────────────────────────────────────────────
      // TYPEWRITER
      // ─────────────────────────────────────────────────────
      case "typewriter":
        return (
          <TypewriterText
            text={content}
            speed={animation.typewriterSpeed ?? 2}
            delay={0}
            showCursor={animation.showCursor ?? true}
            style={textStyles}
          />
        );

      // ─────────────────────────────────────────────────────
      // STAGGER (words animate in sequence)
      // ─────────────────────────────────────────────────────
      case "stagger":
        return (
          <StaggeredText
            text={content}
            by={animation.staggerBy ?? "word"}
            staggerDelay={animation.staggerDelay ?? 4}
            style={textStyles}
          />
        );

      // ─────────────────────────────────────────────────────
      // REVEAL (mask wipe)
      // ─────────────────────────────────────────────────────
      case "reveal":
        return (
          <RevealText
            text={content}
            direction={animation.revealDirection ?? "left"}
            duration={enterDuration}
            style={textStyles}
          />
        );

      // ─────────────────────────────────────────────────────
      // COUNTUP (number animation)
      // ─────────────────────────────────────────────────────
      case "countup":
        const targetNumber = parseFloat(content) || 0;
        return (
          <CountUpText
            from={animation.countupFrom ?? 0}
            to={targetNumber}
            duration={enterDuration}
            delay={0}
            prefix={animation.countupPrefix ?? ""}
            suffix={animation.countupSuffix ?? ""}
            decimals={animation.countupDecimals ?? 0}
            style={textStyles}
          />
        );

      // ─────────────────────────────────────────────────────
      // GLITCH (distortion effect)
      // ─────────────────────────────────────────────────────
      case "glitch":
        return (
          <GlitchText
            text={content}
            intensity={animation.glitchIntensity ?? 1.0}
            delay={0}
            duration={enterDuration}
            style={textStyles}
          />
        );

      // ─────────────────────────────────────────────────────
      // HIGHLIGHT (animated underline/background)
      // ─────────────────────────────────────────────────────
      case "highlight":
        return (
          <HighlightText
            text={content}
            highlightColor={style.highlightColor ?? theme.colors.primary}
            delay={0}
            duration={enterDuration}
            type={animation.highlightType ?? "underline"}
            style={textStyles}
          />
        );

      // ─────────────────────────────────────────────────────
      // POP (bouncy scale with overshoot)
      // ─────────────────────────────────────────────────────
      case "pop":
        return (
          <PopIn delay={0}>
            <div style={textStyles}>{content}</div>
          </PopIn>
        );

      // ─────────────────────────────────────────────────────
      // SCALE (punchy 0.85 → 1)
      // ─────────────────────────────────────────────────────
      case "scale":
        return (
          <ScaleIn delay={0} duration={enterDuration} startScale={0.85} endScale={1}>
            <div style={textStyles}>{content}</div>
          </ScaleIn>
        );

      // ─────────────────────────────────────────────────────
      // SLIDES (4 directions)
      // ─────────────────────────────────────────────────────
      case "slide_up":
        return (
          <SlideIn direction="bottom" delay={0} duration={enterDuration} distance={50}>
            <div style={textStyles}>{content}</div>
          </SlideIn>
        );

      case "slide_down":
        return (
          <SlideIn direction="top" delay={0} duration={enterDuration} distance={50}>
            <div style={textStyles}>{content}</div>
          </SlideIn>
        );

      case "slide_left":
        return (
          <SlideIn direction="right" delay={0} duration={enterDuration} distance={60}>
            <div style={textStyles}>{content}</div>
          </SlideIn>
        );

      case "slide_right":
        return (
          <SlideIn direction="left" delay={0} duration={enterDuration} distance={60}>
            <div style={textStyles}>{content}</div>
          </SlideIn>
        );

      // ─────────────────────────────────────────────────────
      // NONE (instant appear)
      // ─────────────────────────────────────────────────────
      case "none":
        return <div style={textStyles}>{content}</div>;

      // ─────────────────────────────────────────────────────
      // FADE (default)
      // ─────────────────────────────────────────────────────
      case "fade":
      default:
        return (
          <FadeIn delay={0} duration={enterDuration}>
            <div style={textStyles}>{content}</div>
          </FadeIn>
        );
    }
  };

  return (
    <div style={{ ...positionStyles, zIndex: layer.zIndex }}>
      {wrapWithExit(renderAnimatedText())}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Clip Renderer
// ─────────────────────────────────────────────────────────────

const ClipRenderer: React.FC<{
  clip: Clip;
  fps: number;
}> = ({ clip, fps }) => {
  const frame = useCurrentFrame();
  const { durationFrames, layers, enterTransition, exitTransition, backgroundColor } = clip;

  // Enter transition
  let clipOpacity = 1;
  let clipTransform = "";

  if (enterTransition && enterTransition.type !== "none") {
    const enterProgress = Math.min(1, frame / enterTransition.durationFrames);

    switch (enterTransition.type) {
      case "fade":
        clipOpacity = interpolate(enterProgress, [0, 1], [0, 1], { extrapolateRight: "clamp" });
        break;
      case "slide":
      case "slide_left":
        clipTransform = `translateX(${interpolate(enterProgress, [0, 1], [100, 0])}%)`;
        clipOpacity = enterProgress;
        break;
      case "slide_right":
        clipTransform = `translateX(${interpolate(enterProgress, [0, 1], [-100, 0])}%)`;
        clipOpacity = enterProgress;
        break;
      case "slide_up":
        clipTransform = `translateY(${interpolate(enterProgress, [0, 1], [100, 0])}%)`;
        clipOpacity = enterProgress;
        break;
      case "slide_down":
        clipTransform = `translateY(${interpolate(enterProgress, [0, 1], [-100, 0])}%)`;
        clipOpacity = enterProgress;
        break;
    }
  }

  // Exit transition
  if (exitTransition && exitTransition.type !== "none") {
    const exitStart = durationFrames - exitTransition.durationFrames;
    if (frame > exitStart) {
      const exitProgress = (frame - exitStart) / exitTransition.durationFrames;

      switch (exitTransition.type) {
        case "fade":
          clipOpacity *= interpolate(exitProgress, [0, 1], [1, 0], { extrapolateRight: "clamp" });
          break;
        case "slide":
        case "slide_left":
          clipTransform = `translateX(${interpolate(exitProgress, [0, 1], [0, -100])}%)`;
          break;
        case "slide_right":
          clipTransform = `translateX(${interpolate(exitProgress, [0, 1], [0, 100])}%)`;
          break;
      }
    }
  }

  // Sort layers by zIndex
  const sortedLayers = [...layers].sort((a, b) => a.zIndex - b.zIndex);

  // Check if this is a text-only clip
  const hasRealImages = sortedLayers.some(
    (l) => (l.type === "image" || l.type === "generated_image") &&
      l.src && !l.src.startsWith("none://") && l.src !== ""
  );
  const hasBackgroundLayer = sortedLayers.some((l) => l.type === "background");

  return (
    <AbsoluteFill
      style={{
        opacity: clipOpacity,
        transform: clipTransform || undefined,
        backgroundColor: !hasRealImages && !hasBackgroundLayer
          ? (backgroundColor ?? theme.colors.backgroundDark)
          : (backgroundColor ?? "transparent"),
      }}
    >
      {sortedLayers.map((layer, i) => {
        const key = `${clip.id}-layer-${i}`;

        switch (layer.type) {
          case "background":
            return <BackgroundLayerRenderer key={key} layer={layer} />;
          case "image":
          case "generated_image":
            return (
              <ImageLayerRenderer
                key={key}
                layer={layer}
                clipFrame={frame}
                clipDuration={durationFrames}
              />
            );
          case "text":
            return (
              <TextLayerRenderer
                key={key}
                layer={layer}
                clipFrame={frame}
                clipDuration={durationFrames}
                fps={fps}
              />
            );
          default:
            return null;
        }
      })}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// Audio Track
// ─────────────────────────────────────────────────────────────

const AudioTrack: React.FC<{
  audio: z.infer<typeof audioSchema>;
  totalDuration: number;
}> = ({ audio, totalDuration }) => {
  const frame = useCurrentFrame();

  const fadeIn = audio.fadeIn ?? 30;
  const fadeOut = audio.fadeOut ?? 30;
  const volume = audio.volume ?? 0.5;

  const fadeOutStart = totalDuration - fadeOut;

  const volumeMultiplier = interpolate(
    frame,
    [0, fadeIn, fadeOutStart, totalDuration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <Audio
      src={audio.src}
      volume={volume * volumeMultiplier}
      startFrom={audio.startFrame ?? 0}
      loop={audio.loop}
    />
  );
};

// ─────────────────────────────────────────────────────────────
// Main Composition
// ─────────────────────────────────────────────────────────────

export const ProductVideo: React.FC<ProductVideoProps> = ({
  meta,
  clips,
  audio,
  backgroundColor: globalBg
}) => {
  const { fps, durationInFrames } = useVideoConfig();

  // Empty state
  if (!clips || clips.length === 0) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor: globalBg ?? theme.colors.background,
          justifyContent: "center",
          alignItems: "center",
          fontFamily,
        }}
      >
        <div style={{ color: theme.colors.textMuted, fontSize: 32 }}>
          No clips provided
        </div>
        <div style={{ color: theme.colors.textDark, fontSize: 18, marginTop: 16 }}>
          VideoSpec: {meta?.title ?? "untitled"}
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ backgroundColor: globalBg ?? theme.colors.backgroundDark }}>
      {/* Audio track */}
      {audio && <AudioTrack audio={audio} totalDuration={durationInFrames} />}

      {/* Clips */}
      {clips.map((clip) => (
        <Sequence
          key={clip.id}
          from={clip.startFrame}
          durationInFrames={clip.durationFrames}
        >
          <ClipRenderer clip={clip} fps={fps} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
