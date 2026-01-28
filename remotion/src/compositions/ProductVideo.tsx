/**
 * ProductVideo Composition - FULLY ENHANCED
 * 
 * Main composition for rendering product videos from VideoSpec JSON.
 * FULL ANIMATION SUPPORT with RAG knowledge integration:
 * - 15+ text animations (added wave)
 * - 10+ background types (orbs, mesh, aurora, particles)
 * - 12+ image transforms (zoom_drift, micro_motion, keyframe pan)
 * - 2 new layer types (connector, button)
 * - Custom easing/bezier support
 * - Continuous motion post-entrance
 * - Irregular stagger arrays
 * 
 * Animation Philosophy:
 * - snappy: Fast, no bounce (corporate, professional)
 * - smooth: Medium speed, gentle ease (elegant, premium)
 * - bouncy: Overshoot and settle (playful, energetic)
 * - kinetic: Energetic with slight overshoot
 * - elegant: Luxurious, no overshoot
 * - anticipate: Anticipation + overshoot
 * 
 * POSITIONING SYSTEM (v2):
 * - Coordinates {x, y} are canvas percentages (0-100)
 * - "anchor" determines what part of element sits at coordinate
 * - Default anchor: "center" → element center at (x, y)
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
import { 
  KenBurns, 
  FocusZoom, 
  ParallaxImage,
} from "../components/KenBurns";
import { DeviceFrame } from "../components/DeviceFrame";
import {
  TypewriterText,
  StaggeredText,
  RevealText,
  CountUpText,
  GlitchText,
  HighlightText,
  WaveText,
} from "../components/AnimatedText";
import { FadeIn, SlideIn, ScaleIn, PopIn } from "../components";
import {
  OrbsBackground,
  GradientBackground,
  GridBackground,
  NoiseBackground,
  RadialGradientBackground,
  MeshGradientBackground,
  AuroraBackground,
  ParticlesBackground,
} from "../components/Background";
import { ConnectorLine } from "../components/ConnectorLine";
import { ButtonLayer } from "../components/ButtonLayer";
import { 
  SPRING_CONFIGS as EASING_SPRING_CONFIGS,
  getEasingFromString,
  AnimationFeel as EasingAnimationFeel,
} from "../lib/easing";

const { fontFamily } = loadFont('normal', {
  weights: ['400', '600', '700'],
  subsets: ['latin'],
  ignoreTooManyRequestsWarning: true,
});

// ─────────────────────────────────────────────────────────────
// Spring Physics Presets (Extended)
// ─────────────────────────────────────────────────────────────

const SPRING_CONFIGS = {
  snappy: { damping: 25, stiffness: 400, mass: 0.3 },
  smooth: { damping: 20, stiffness: 150, mass: 0.5 },
  bouncy: { damping: 8, stiffness: 200, mass: 0.5 },
  kinetic: { damping: 12, stiffness: 300, mass: 0.4 },
  elegant: { damping: 18, stiffness: 100, mass: 0.6 },
  anticipate: { damping: 10, stiffness: 250, mass: 0.5 },
  gentle: { damping: 15, stiffness: 80, mass: 0.8 },
  sharp: { damping: 30, stiffness: 500, mass: 0.2 },
  wobbly: { damping: 5, stiffness: 180, mass: 0.6 },
} as const;

type AnimationFeel = keyof typeof SPRING_CONFIGS;

// ─────────────────────────────────────────────────────────────
// Schema - Enhanced with RAG Knowledge
// ─────────────────────────────────────────────────────────────

// Custom spring config schema
const springConfigSchema = z.object({
  damping: z.number(),
  stiffness: z.number(),
  mass: z.number(),
}).optional();

// Continuous motion config (post-entrance)
const continuousMotionSchema = z.object({
  type: z.enum(["oscillate", "pulse", "drift", "breathe"]),
  intensity: z.number().optional(),
  speed: z.number().optional(),
}).optional();

// Enhanced transform schema with new motion types
const transformSchema = z.object({
  type: z.enum([
    // Original
    "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down",
    "static", "focus", "ken_burns", "parallax",
    // NEW from RAG
    "zoom_drift",      // Combined subtle zoom + drift
    "subtle_drift",    // Very gentle position drift
    "micro_motion",    // Barely perceptible movement
    "breathe",         // Subtle scale oscillation
  ]),
  startScale: z.number().optional(),
  endScale: z.number().optional(),
  focusX: z.number().optional(),
  focusY: z.number().optional(),
  intensity: z.number().optional(),
  parallaxSpeed: z.number().optional(),
  parallaxDirection: z.enum(["horizontal", "vertical"]).optional(),
  // NEW: Drift amounts for zoom_drift mode
  driftX: z.number().optional(),
  driftY: z.number().optional(),
  // NEW: Custom easing
  easing: z.string().optional(),
  // NEW: Keyframe pan support
  panKeyframes: z.array(z.object({
    frame: z.number(),
    x: z.number(),
    y: z.number(),
    scale: z.number().optional(),
    hold: z.number().optional(),
  })).optional(),
});

const opacitySchema = z.object({
  start: z.number(),
  end: z.number(),
});

const positionSchema = z.object({
  preset: z.enum([
    "center", "top", "bottom", "left", "right",
    "top_left", "top_right", "bottom_left", "bottom_right",
    "top-left", "top-right", "bottom-left", "bottom-right"
  ]).optional(),
  x: z.number().optional(),
  y: z.number().optional(),
  anchor: z.enum(["center", "top-left", "top-right", "bottom-left", "bottom-right"]).optional(),
});

// Enhanced text animation schema
const textAnimationSchema = z.object({
  enter: z.enum([
    "fade", "scale", "pop", "slide_up", "slide_down", "slide_left", "slide_right",
    "typewriter", "stagger", "reveal", "glitch", "highlight", "countup", "none",
    // NEW from RAG
    "wave",           // Wave animation (was missing from enum!)
  ]),
  exit: z.enum(["fade", "slide_up", "slide_down", "scale", "none"]).optional(),
  enterDuration: z.number().optional(),
  exitDuration: z.number().optional(),
  // NEW: Duration in ms alternative (auto-converts)
  enterDurationMs: z.number().optional(),
  feel: z.enum([
    "snappy", "smooth", "bouncy", 
    // NEW extended feels
    "kinetic", "elegant", "anticipate", "gentle", "sharp", "wobbly"
  ]).optional(),
  // NEW: Custom spring config (overrides feel)
  springConfig: springConfigSchema,
  // NEW: Custom easing string (e.g., "cubic-bezier(0.34, 1.56, 0.64, 1)")
  easing: z.string().optional(),
  // NEW: Continuous motion post-entrance
  continuousMotion: continuousMotionSchema,
  // Typewriter options
  typewriterSpeed: z.number().optional(),
  showCursor: z.boolean().optional(),
  cursorBlinkSpeed: z.number().optional(),
  deleteAfter: z.number().optional(),
  // Stagger options - ENHANCED
  staggerBy: z.enum(["word", "character"]).optional(),
  staggerDelay: z.union([z.number(), z.array(z.number())]).optional(), // NEW: Array support for irregular stagger
  staggerAnimation: z.enum(["fade", "slide", "both"]).optional(),       // NEW: Per-element animation type
  durationVariance: z.number().optional(),                              // NEW: ±frames variance
  // Reveal options
  revealDirection: z.enum(["left", "right", "top", "bottom"]).optional(),
  // Highlight options
  highlightType: z.enum(["underline", "background"]).optional(),
  // Countup options
  countupFrom: z.number().optional(),
  countupDecimals: z.number().optional(),
  countupPrefix: z.string().optional(),
  countupSuffix: z.string().optional(),
  // Glitch options
  glitchIntensity: z.number().optional(),
  // NEW: Wave options
  waveAmplitude: z.number().optional(),
  waveFrequency: z.number().optional(),
  waveSpeed: z.number().optional(),
});

// Enhanced text style schema
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
  // NEW: Multi-layer shadows (RAG: depth shadow technique)
  shadows: z.array(z.object({
    blur: z.number(),
    opacity: z.number(),
    offsetX: z.number().optional(),
    offsetY: z.number().optional(),
    color: z.string().optional(),
  })).optional(),
});

// Layer schemas
const imageLayerSchema = z.object({
  type: z.literal("image"),
  src: z.string(),
  zIndex: z.number(),
  position: positionSchema.optional(),
  scale: z.number().optional(),
  transform: transformSchema.optional(),
  opacity: opacitySchema.optional(),
  device: z.enum(["none", "iphone", "iphonePro", "macbook", "ipad"]).optional(),
  startFrame: z.number().optional(),
  durationFrames: z.number().optional(),
  // NEW: Parallax layer designation
  parallaxLayer: z.enum(["background", "content", "foreground"]).optional(),
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

// Enhanced gradient spec
const gradientSpecSchema = z.object({
  colors: z.array(z.string()),
  angle: z.number().optional(),
  animate: z.boolean().optional(),
  // NEW: Custom animation range
  animateAngleRange: z.tuple([z.number(), z.number()]).optional(),
  animateSpeed: z.number().optional(),
});

// Mesh gradient point schema (NEW)
const meshPointSchema = z.object({
  x: z.number(),
  y: z.number(),
  color: z.string(),
  size: z.number().optional(),
  blur: z.number().optional(),
});

// Enhanced background layer schema
const backgroundLayerSchema = z.object({
  type: z.literal("background"),
  zIndex: z.number(),
  color: z.string().optional(),
  gradient: gradientSpecSchema.optional(),
  opacity: opacitySchema.optional(),
  
  // Orbs - ENHANCED
  orbs: z.boolean().optional(),
  orbColors: z.array(z.string()).optional(),
  orbCount: z.number().optional(),                                    // NEW: Explicit count
  orbPositions: z.array(z.object({ x: z.number(), y: z.number() })).optional(), // NEW: Manual positions
  orbOpacity: z.number().optional(),                                  // NEW: 0-1 opacity
  orbBlur: z.number().optional(),                                     // NEW: Blur in px
  orbDriftSpeed: z.number().optional(),                               // NEW: Drift speed 0-10
  orbSizeRange: z.tuple([z.number(), z.number()]).optional(),         // NEW: [min, max] sizes
  
  // Grid - ENHANCED
  grid: z.boolean().optional(),
  gridSize: z.number().optional(),
  gridColor: z.string().optional(),
  gridAnimated: z.boolean().optional(),
  gridLineWidth: z.number().optional(),                               // NEW
  gridFadeEdges: z.boolean().optional(),                              // NEW
  gridPerspective: z.boolean().optional(),                            // NEW
  
  // Noise - ENHANCED
  noise: z.boolean().optional(),
  noiseOpacity: z.number().optional(),
  noiseGrainSize: z.enum(["fine", "medium", "coarse"]).optional(),    // NEW
  noiseAnimated: z.boolean().optional(),                              // NEW
  
  // Radial - ENHANCED
  radial: z.boolean().optional(),
  radialCenterX: z.number().optional(),
  radialCenterY: z.number().optional(),
  radialCenterColor: z.string().optional(),
  radialEdgeColor: z.string().optional(),
  radialAnimate: z.boolean().optional(),                              // NEW
  radialDriftRange: z.number().optional(),                            // NEW
  
  // NEW: Mesh gradient (RAG feature)
  mesh: z.boolean().optional(),
  meshPoints: z.array(meshPointSchema).optional(),
  meshAnimate: z.boolean().optional(),
  meshDriftAmount: z.number().optional(),
  
  // NEW: Aurora background
  aurora: z.boolean().optional(),
  auroraColors: z.array(z.string()).optional(),
  auroraSpeed: z.number().optional(),
  auroraIntensity: z.number().optional(),
  
  // NEW: Particles background
  particles: z.boolean().optional(),
  particleCount: z.number().optional(),
  particleColor: z.string().optional(),
  particleDirection: z.enum(["up", "down", "left", "right"]).optional(),
  particleSizeRange: z.tuple([z.number(), z.number()]).optional(),
});

// NEW: Connector line layer schema (RAG feature)
const connectorLayerSchema = z.object({
  type: z.literal("connector"),
  zIndex: z.number(),
  from: z.object({ x: z.number(), y: z.number() }),
  to: z.object({ x: z.number(), y: z.number() }),
  waypoints: z.array(z.object({ x: z.number(), y: z.number() })).optional(),
  color: z.string().optional(),
  strokeWidth: z.number().optional(),
  lineStyle: z.enum(["solid", "dashed", "dotted"]).optional(),
  startEnd: z.enum(["none", "arrow", "dot", "diamond"]).optional(),
  endEnd: z.enum(["none", "arrow", "dot", "diamond"]).optional(),
  delay: z.number().optional(),
  duration: z.number().optional(),
  direction: z.enum(["forward", "reverse", "both"]).optional(),
  feel: z.enum(["snappy", "smooth", "bouncy"]).optional(),
  easing: z.string().optional(),
  glow: z.boolean().optional(),
  glowColor: z.string().optional(),
  glowIntensity: z.number().optional(),
});

// NEW: Button layer schema (RAG feature)
const buttonLayerSchema = z.object({
  type: z.literal("button"),
  zIndex: z.number(),
  text: z.string(),
  x: z.number().optional(),
  y: z.number().optional(),
  width: z.number().optional(),
  height: z.number().optional(),
  variant: z.enum(["solid", "outline", "ghost", "gradient"]).optional(),
  fillColor: z.string().optional(),
  textColor: z.string().optional(),
  borderColor: z.string().optional(),
  borderWidth: z.number().optional(),
  borderRadius: z.number().optional(),
  gradientColors: z.array(z.string()).optional(),
  gradientAngle: z.number().optional(),
  fontSize: z.number().optional(),
  fontWeight: z.number().optional(),
  letterSpacing: z.string().optional(),
  icon: z.string().optional(),
  iconPosition: z.enum(["left", "right"]).optional(),
  shadow: z.boolean().optional(),
  shadowColor: z.string().optional(),
  shadowBlur: z.number().optional(),
  enterAnimation: z.enum(["fade", "scale", "slide_up", "slide_down", "pop", "none"]).optional(),
  delay: z.number().optional(),
  duration: z.number().optional(),
  feel: z.enum(["snappy", "smooth", "bouncy"]).optional(),
  pulse: z.boolean().optional(),
  pulseScale: z.number().optional(),
  pulseDuration: z.number().optional(),
  startFrame: z.number().optional(),
  durationFrames: z.number().optional(),
});

const layerSchema = z.discriminatedUnion("type", [
  imageLayerSchema,
  generatedImageLayerSchema,
  textLayerSchema,
  backgroundLayerSchema,
  connectorLayerSchema,  // NEW
  buttonLayerSchema,     // NEW
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
// Background Layer Renderer (10+ types)
// ─────────────────────────────────────────────────────────────

const BackgroundLayerRenderer: React.FC<{
  layer: z.infer<typeof backgroundLayerSchema>;
}> = ({ layer }) => {
  const baseColor = layer.color || theme.colors.backgroundDark;
  const bgOpacity = layer.opacity ? layer.opacity.start : 1.0;

  // Priority: aurora > particles > mesh > radial > orbs > gradient > grid/noise > solid
  
  // Aurora background (NEW)
  if (layer.aurora) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex, opacity: bgOpacity }}>
        <AuroraBackground
          colors={layer.auroraColors}
          baseColor={baseColor}
          speed={layer.auroraSpeed}
          intensity={layer.auroraIntensity}
        />
      </AbsoluteFill>
    );
  }
  
  // Particles background (NEW)
  if (layer.particles) {
    const [minSize, maxSize] = layer.particleSizeRange || [2, 6];
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex, opacity: bgOpacity }}>
        <ParticlesBackground
          count={layer.particleCount}
          color={layer.particleColor}
          baseColor={baseColor}
          direction={layer.particleDirection}
          minSize={minSize}
          maxSize={maxSize}
        />
      </AbsoluteFill>
    );
  }
  
  // Mesh gradient (NEW)
  if (layer.mesh && layer.meshPoints) {
    // Convert meshPoints to array if it's a number (fallback for legacy specs)
    let points = layer.meshPoints;
    if (typeof points === 'number') {
      // Generate default mesh points based on count
      const count = Math.min(Math.max(points, 4), 7); // 4-7 points recommended
      const colors = layer.orbColors || [theme.colors.primary, theme.colors.accent, theme.colors.accentAlt];
      const positions = [
        { x: 20, y: 20 }, { x: 80, y: 20 },
        { x: 20, y: 80 }, { x: 80, y: 80 },
        { x: 50, y: 30 }, { x: 30, y: 60 }, { x: 70, y: 70 }
      ];

      points = Array.from({ length: count }, (_, i) => ({
        x: positions[i % positions.length].x,
        y: positions[i % positions.length].y,
        color: colors[i % colors.length],
        size: 500,
        blur: 80,
      }));
    }

    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex, opacity: bgOpacity }}>
        <MeshGradientBackground
          points={points}
          baseColor={baseColor}
          animate={layer.meshAnimate}
          driftAmount={layer.meshDriftAmount}
        />
      </AbsoluteFill>
    );
  }
  
  // Radial gradient spotlight
  if (layer.radial) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex, opacity: bgOpacity }}>
        <RadialGradientBackground
          centerColor={layer.radialCenterColor || theme.colors.backgroundLight}
          edgeColor={layer.radialEdgeColor || theme.colors.backgroundDark}
          centerX={layer.radialCenterX ?? 50}
          centerY={layer.radialCenterY ?? 50}
          animate={layer.radialAnimate}
          driftRange={layer.radialDriftRange}
        />
      </AbsoluteFill>
    );
  }

  // Animated glowing orbs (ENHANCED)
  if (layer.orbs) {
    const colors = layer.orbColors || [theme.colors.primary, theme.colors.accent, theme.colors.accentAlt];
    const [minSize, maxSize] = layer.orbSizeRange || [350, 600];
    
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex, opacity: bgOpacity }}>
        <OrbsBackground
          orbColors={colors}
          orbCount={layer.orbCount}
          orbPositions={layer.orbPositions}
          orbOpacity={layer.orbOpacity}
          orbBlur={layer.orbBlur}
          orbDriftSpeed={layer.orbDriftSpeed}
          sizeRange={[minSize, maxSize]}
          baseColor={baseColor}
        />
      </AbsoluteFill>
    );
  }

  // Linear gradient (ENHANCED)
  if (layer.gradient) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex, opacity: bgOpacity }}>
        <GradientBackground
          colors={layer.gradient.colors}
          angle={layer.gradient.angle ?? 180}
          animate={layer.gradient.animate ?? false}
          animateAngleRange={layer.gradient.animateAngleRange}
          animateSpeed={layer.gradient.animateSpeed}
        />
      </AbsoluteFill>
    );
  }

  // Grid pattern (ENHANCED)
  if (layer.grid) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex, opacity: bgOpacity }}>
        <GridBackground
          color={baseColor}
          lineColor={layer.gridColor || theme.colors.overlayLight}
          gridSize={layer.gridSize ?? 40}
          animated={layer.gridAnimated ?? false}
          lineWidth={layer.gridLineWidth}
          fadeEdges={layer.gridFadeEdges}
          perspective={layer.gridPerspective}
        />
      </AbsoluteFill>
    );
  }

  // Noise texture (ENHANCED)
  if (layer.noise) {
    return (
      <AbsoluteFill style={{ zIndex: layer.zIndex, opacity: bgOpacity }}>
        <NoiseBackground
          color={baseColor}
          opacity={layer.noiseOpacity ?? 0.05}
          grainSize={layer.noiseGrainSize}
          animate={layer.noiseAnimated}
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
        opacity: bgOpacity,
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────
// Image Layer Renderer (12+ transforms)
// ─────────────────────────────────────────────────────────────

const ImageLayerRenderer: React.FC<{
  layer: z.infer<typeof imageLayerSchema> | z.infer<typeof generatedImageLayerSchema>;
  clipFrame: number;
  clipDuration: number;
}> = ({ layer, clipFrame, clipDuration }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const progress = clipDuration > 0 ? clipFrame / clipDuration : 0;

  // Skip if src is invalid
  if (!layer.src || layer.src.startsWith("none://") || layer.src === "") {
    return null;
  }

  // Handle relative paths
  let imageSrc = layer.src;
  if (!layer.src.startsWith("http://") && !layer.src.startsWith("https://")) {
    const cleanPath = layer.src.startsWith("/") ? layer.src.slice(1) : layer.src;
    imageSrc = staticFile(cleanPath);
  }

  // Opacity animation
  let opacity = 1;
  if (layer.opacity) {
    opacity = interpolate(progress, [0, 1], [layer.opacity.start, layer.opacity.end], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  }

  // Position and scale handling
  const layerScale = 'scale' in layer ? layer.scale : 1.0;
  const layerPosition = 'position' in layer ? layer.position : undefined;
  const anchor = layerPosition?.anchor || "center";

  // Calculate position styles
  const positionStyles: React.CSSProperties = {};
  if (layerPosition?.x !== undefined && layerPosition?.y !== undefined) {
    positionStyles.position = 'absolute';
    positionStyles.left = `${layerPosition.x}%`;
    positionStyles.top = `${layerPosition.y}%`;
    
    switch (anchor) {
      case "center":
        positionStyles.transform = `translate(-50%, -50%) scale(${layerScale})`;
        break;
      case "top-left":
        positionStyles.transform = `translate(0, 0) scale(${layerScale})`;
        break;
      case "top-right":
        positionStyles.transform = `translate(-100%, 0) scale(${layerScale})`;
        break;
      case "bottom-left":
        positionStyles.transform = `translate(0, -100%) scale(${layerScale})`;
        break;
      case "bottom-right":
        positionStyles.transform = `translate(-100%, -100%) scale(${layerScale})`;
        break;
    }
  } else {
    positionStyles.width = '100%';
    positionStyles.height = '100%';
  }

  // Device frame handling
  const device = "device" in layer ? layer.device : undefined;
  if (device && device !== "none") {
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
        <div style={positionStyles}>
          <DeviceFrame
            screenshot={cleanScreenshotPath}
            device={device}
            scale={device === "macbook" ? 0.6 : device === "ipad" ? 0.55 : 0.8}
            animated={false}
          />
        </div>
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

    // Focus zoom
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

    // NEW: Zoom + drift combo
    if (t.type === "zoom_drift") {
      return (
        <AbsoluteFill style={{ zIndex: layer.zIndex, opacity }}>
          <KenBurns
            src={layer.src}
            direction="zoom-drift"
            intensity={intensity}
            startScale={t.startScale}
            endScale={t.endScale}
            driftX={t.driftX}
            driftY={t.driftY}
            easing={t.easing}
          />
        </AbsoluteFill>
      );
    }

    // NEW: Subtle drift (micro motion)
    if (t.type === "subtle_drift" || t.type === "micro_motion") {
      return (
        <AbsoluteFill style={{ zIndex: layer.zIndex, opacity }}>
          <KenBurns
            src={layer.src}
            direction="micro-motion"
            intensity={intensity * 0.3}
            driftX={t.driftX ?? 1}
            driftY={t.driftY ?? 1}
          />
        </AbsoluteFill>
      );
    }

    // NEW: Breathe (subtle scale oscillation)
    if (t.type === "breathe") {
      return (
        <AbsoluteFill style={{ zIndex: layer.zIndex, opacity }}>
          <KenBurns
            src={layer.src}
            direction="breathe"
            intensity={intensity * 0.5}
            startScale={t.startScale ?? 0.98}
            endScale={t.endScale ?? 1.02}
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
            startScale={t.startScale}
            endScale={t.endScale}
            easing={t.easing}
          />
        </AbsoluteFill>
      );
    }
  }

  // Static image
  return (
    <AbsoluteFill style={{ zIndex: layer.zIndex, opacity }}>
      <div style={positionStyles}>
        <Img
          src={layer.src}
          style={{
            width: positionStyles.width || "auto",
            height: positionStyles.height || "auto",
            objectFit: "cover",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// Text Layer Renderer (15+ enter animations)
// ─────────────────────────────────────────────────────────────

const TextLayerRenderer: React.FC<{
  layer: z.infer<typeof textLayerSchema>;
  clipFrame: number;
  clipDuration: number;
  fps: number;
}> = ({ layer, clipFrame, clipDuration, fps }) => {
  const frame = useCurrentFrame();
  const { content, style, animation, position, startFrame = 0, durationFrames } = layer;

  // Check visibility
  const localFrame = clipFrame - startFrame;
  const textDuration = durationFrames ?? clipDuration - startFrame;

  if (localFrame < 0) return null;
  if (durationFrames && localFrame > durationFrames) return null;

  // Animation parameters
  const enterDuration = animation.enterDurationMs 
    ? Math.round(animation.enterDurationMs * fps / 1000)
    : (animation.enterDuration ?? 10);
  const exitDuration = animation.exitDuration ?? Math.round(enterDuration * 0.8); // RAG: exit 20% shorter
  const feel: AnimationFeel = (animation.feel as AnimationFeel) ?? "snappy";
  const springConfig = animation.springConfig || SPRING_CONFIGS[feel] || SPRING_CONFIGS.snappy;

  // Exit animation progress
  const exitStart = textDuration - exitDuration;
  const isExiting = localFrame > exitStart && animation.exit !== "none";

  // Build multi-layer shadow if specified
  const buildTextShadow = (): string | undefined => {
    if (style.shadows && style.shadows.length > 0) {
      return style.shadows.map(s => {
        const color = s.color || `rgba(0,0,0,${s.opacity})`;
        const x = s.offsetX ?? 0;
        const y = s.offsetY ?? s.blur * 0.5;
        return `${x}px ${y}px ${s.blur}px ${color}`;
      }).join(", ");
    }
    return style.textShadow;
  };

  // Position styles with anchor point system
  const positionStyles: React.CSSProperties = {
    position: "absolute",
    display: "flex",
    padding: theme.spacing.safe,
  };

  const anchor = position.anchor ?? "center";
  const rawPreset = position.preset ?? "";
  const preset = rawPreset.replace(/-/g, "_");

  // Handle presets
  if (preset) {
    switch (preset) {
      case "center":
        positionStyles.inset = 0;
        positionStyles.justifyContent = "center";
        positionStyles.alignItems = "center";
        break;
      case "top":
        positionStyles.top = 0;
        positionStyles.left = 0;
        positionStyles.right = 0;
        positionStyles.height = "auto";
        positionStyles.paddingTop = theme.spacing.safe * 2;
        positionStyles.justifyContent = "center";
        positionStyles.alignItems = "flex-start";
        break;
      case "bottom":
        positionStyles.bottom = 0;
        positionStyles.left = 0;
        positionStyles.right = 0;
        positionStyles.height = "auto";
        positionStyles.paddingBottom = theme.spacing.safe * 2;
        positionStyles.justifyContent = "center";
        positionStyles.alignItems = "flex-end";
        break;
      case "left":
        positionStyles.left = 0;
        positionStyles.top = 0;
        positionStyles.bottom = 0;
        positionStyles.width = "50%";
        positionStyles.justifyContent = "flex-start";
        positionStyles.alignItems = "center";
        break;
      case "right":
        positionStyles.right = 0;
        positionStyles.top = 0;
        positionStyles.bottom = 0;
        positionStyles.width = "50%";
        positionStyles.justifyContent = "flex-end";
        positionStyles.alignItems = "center";
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
  } else if (position.x !== undefined || position.y !== undefined) {
    if (position.x !== undefined) positionStyles.left = `${position.x}%`;
    if (position.y !== undefined) positionStyles.top = `${position.y}%`;
    
    switch (anchor) {
      case "center":
        positionStyles.transform = "translate(-50%, -50%)";
        positionStyles.justifyContent = "center";
        positionStyles.alignItems = "center";
        break;
      case "top-left":
        positionStyles.transform = "translate(0, 0)";
        positionStyles.justifyContent = "flex-start";
        positionStyles.alignItems = "flex-start";
        break;
      case "top-right":
        positionStyles.transform = "translate(-100%, 0)";
        positionStyles.justifyContent = "flex-end";
        positionStyles.alignItems = "flex-start";
        break;
      case "bottom-left":
        positionStyles.transform = "translate(0, -100%)";
        positionStyles.justifyContent = "flex-start";
        positionStyles.alignItems = "flex-end";
        break;
      case "bottom-right":
        positionStyles.transform = "translate(-100%, -100%)";
        positionStyles.justifyContent = "flex-end";
        positionStyles.alignItems = "flex-end";
        break;
    }
  } else {
    positionStyles.inset = 0;
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
    textShadow: buildTextShadow(),
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

  // Continuous motion wrapper
  const wrapWithContinuousMotion = (children: React.ReactNode) => {
    if (!animation.continuousMotion || localFrame < enterDuration) {
      return children;
    }

    const motionFrame = localFrame - enterDuration;
    const { type, intensity = 1, speed = 60 } = animation.continuousMotion;

    let motionStyle: React.CSSProperties = {};

    switch (type) {
      case "oscillate":
        const oscX = Math.sin(motionFrame / speed) * 3 * intensity;
        const oscY = Math.cos(motionFrame / speed * 0.7) * 2 * intensity;
        motionStyle.transform = `translate(${oscX}px, ${oscY}px)`;
        break;
      case "pulse":
        const pulseScale = 1 + Math.sin(motionFrame / speed) * 0.01 * intensity;
        motionStyle.transform = `scale(${pulseScale})`;
        break;
      case "drift":
        const driftX = Math.sin(motionFrame / (speed * 2)) * 5 * intensity;
        motionStyle.transform = `translateX(${driftX}px)`;
        break;
      case "breathe":
        const breatheScale = 1 + Math.sin(motionFrame / speed) * 0.005 * intensity;
        const breatheOpacity = 0.95 + Math.sin(motionFrame / speed) * 0.05;
        motionStyle.transform = `scale(${breatheScale})`;
        motionStyle.opacity = breatheOpacity;
        break;
    }

    return <div style={motionStyle}>{children}</div>;
  };

  // Render based on animation type
  const renderAnimatedText = () => {
    switch (animation.enter) {
      case "typewriter":
        return (
          <TypewriterText
            text={content}
            speed={animation.typewriterSpeed ?? 2}
            delay={0}
            showCursor={animation.showCursor ?? true}
            cursorBlinkSpeed={animation.cursorBlinkSpeed}
            deleteAfter={animation.deleteAfter}
            style={textStyles}
          />
        );

      case "stagger":
        return (
          <StaggeredText
            text={content}
            by={animation.staggerBy ?? "word"}
            staggerDelay={animation.staggerDelay ?? 4}
            staggerAnimation={animation.staggerAnimation}
            durationVariance={animation.durationVariance}
            feel={feel}
            easing={animation.easing}
            springConfig={animation.springConfig}
            style={textStyles}
          />
        );

      case "reveal":
        return (
          <RevealText
            text={content}
            direction={animation.revealDirection ?? "left"}
            duration={enterDuration}
            easing={animation.easing}
            style={textStyles}
          />
        );

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
            easing={animation.easing}
            style={textStyles}
          />
        );

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

      case "highlight":
        return (
          <HighlightText
            text={content}
            highlightColor={style.highlightColor ?? theme.colors.primary}
            delay={0}
            duration={enterDuration}
            type={animation.highlightType ?? "underline"}
            easing={animation.easing}
            style={textStyles}
          />
        );

      // NEW: Wave animation
      case "wave":
        return (
          <WaveText
            text={content}
            amplitude={animation.waveAmplitude ?? 10}
            frequency={animation.waveFrequency ?? 0.5}
            speed={animation.waveSpeed ?? 0.1}
            delay={0}
            style={textStyles}
          />
        );

      case "pop":
        return (
          <PopIn delay={0} easing={animation.easing}>
            <div style={textStyles}>{content}</div>
          </PopIn>
        );

      case "scale":
        return (
          <ScaleIn delay={0} duration={enterDuration} startScale={0.85} endScale={1} easing={animation.easing}>
            <div style={textStyles}>{content}</div>
          </ScaleIn>
        );

      case "slide_up":
        return (
          <SlideIn direction="bottom" delay={0} duration={enterDuration} distance={50} easing={animation.easing}>
            <div style={textStyles}>{content}</div>
          </SlideIn>
        );

      case "slide_down":
        return (
          <SlideIn direction="top" delay={0} duration={enterDuration} distance={50} easing={animation.easing}>
            <div style={textStyles}>{content}</div>
          </SlideIn>
        );

      case "slide_left":
        return (
          <SlideIn direction="right" delay={0} duration={enterDuration} distance={60} easing={animation.easing}>
            <div style={textStyles}>{content}</div>
          </SlideIn>
        );

      case "slide_right":
        return (
          <SlideIn direction="left" delay={0} duration={enterDuration} distance={60} easing={animation.easing}>
            <div style={textStyles}>{content}</div>
          </SlideIn>
        );

      case "none":
        return <div style={textStyles}>{content}</div>;

      case "fade":
      default:
        return (
          <FadeIn delay={0} duration={enterDuration} easing={animation.easing}>
            <div style={textStyles}>{content}</div>
          </FadeIn>
        );
    }
  };

  return (
    <div style={{ ...positionStyles, zIndex: layer.zIndex }}>
      {wrapWithExit(wrapWithContinuousMotion(renderAnimatedText()))}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────
// Connector Layer Renderer (NEW)
// ─────────────────────────────────────────────────────────────

const ConnectorLayerRenderer: React.FC<{
  layer: z.infer<typeof connectorLayerSchema>;
  clipFrame: number;
}> = ({ layer, clipFrame }) => {
  // Handle legacy format: points array [[x1,y1], [x2,y2]]
  let from = layer.from;
  let to = layer.to;

  if (!from || !to) {
    const layerAny = layer as any;
    if (layerAny.points && Array.isArray(layerAny.points) && layerAny.points.length >= 2) {
      const [p1, p2] = layerAny.points;
      from = { x: p1[0], y: p1[1] };
      to = { x: p2[0], y: p2[1] };
    } else {
      console.error('ConnectorLayerRenderer: Invalid layer format', layer);
      return null;
    }
  }

  // Handle legacy format: style object
  const layerAny = layer as any;
  const color = layer.color || layerAny.style?.color || "#ffffff";
  const strokeWidth = layer.strokeWidth || layerAny.style?.width || 2;

  // Handle legacy format: animation object
  const delay = layer.delay || (layerAny.animation?.enter === 'wipe' ? (layerAny.startFrame || 0) : 0);
  const duration = layer.duration || layerAny.animation?.enterDuration || 30;

  return (
    <AbsoluteFill style={{ zIndex: layer.zIndex }}>
      <ConnectorLine
        from={from}
        to={to}
        waypoints={layer.waypoints}
        color={color}
        strokeWidth={strokeWidth}
        lineStyle={layer.lineStyle}
        startEnd={layer.startEnd}
        endEnd={layer.endEnd}
        delay={delay}
        duration={duration}
        direction={layer.direction}
        feel={layer.feel}
        easing={layer.easing}
        glow={layer.glow}
        glowColor={layer.glowColor}
        glowIntensity={layer.glowIntensity}
      />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// Button Layer Renderer (NEW)
// ─────────────────────────────────────────────────────────────

const ButtonLayerRenderer: React.FC<{
  layer: z.infer<typeof buttonLayerSchema>;
  clipFrame: number;
  clipDuration: number;
}> = ({ layer, clipFrame, clipDuration }) => {
  const { startFrame = 0, durationFrames } = layer;

  // Check visibility
  const localFrame = clipFrame - startFrame;
  if (localFrame < 0) return null;
  if (durationFrames && localFrame > durationFrames) return null;

  return (
    <AbsoluteFill style={{ zIndex: layer.zIndex }}>
      <ButtonLayer
        text={layer.text}
        x={layer.x}
        y={layer.y}
        width={layer.width}
        height={layer.height}
        variant={layer.variant}
        fillColor={layer.fillColor}
        textColor={layer.textColor}
        borderColor={layer.borderColor}
        borderWidth={layer.borderWidth}
        borderRadius={layer.borderRadius}
        gradientColors={layer.gradientColors}
        gradientAngle={layer.gradientAngle}
        fontSize={layer.fontSize}
        fontWeight={layer.fontWeight}
        letterSpacing={layer.letterSpacing}
        icon={layer.icon}
        iconPosition={layer.iconPosition}
        shadow={layer.shadow}
        shadowColor={layer.shadowColor}
        shadowBlur={layer.shadowBlur}
        enterAnimation={layer.enterAnimation}
        delay={layer.delay}
        enterDuration={layer.duration}
        feel={layer.feel}
        pulse={layer.pulse}
        pulseScale={layer.pulseScale}
        pulseDuration={layer.pulseDuration}
      />
    </AbsoluteFill>
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
          case "connector":
            return (
              <ConnectorLayerRenderer
                key={key}
                layer={layer}
                clipFrame={frame}
              />
            );
          case "button":
            return (
              <ButtonLayerRenderer
                key={key}
                layer={layer}
                clipFrame={frame}
                clipDuration={durationFrames}
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
