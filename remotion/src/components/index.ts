/**
 * Components Index - FULLY ENHANCED
 * 
 * Exports all animation components with full feature support.
 * Includes all RAG knowledge implementations.
 */

// ─────────────────────────────────────────────────────────────
// ANIMATION WRAPPERS
// ─────────────────────────────────────────────────────────────

export { FadeIn, FadeInOut } from "./FadeIn";
export { SlideIn, SlideUp, SlideDown, SlideLeft, SlideRight } from "./SlideIn";
export { ScaleIn, PopIn, ZoomIn } from "./ScaleIn";

// ─────────────────────────────────────────────────────────────
// TEXT ANIMATIONS
// ─────────────────────────────────────────────────────────────

export {
  TypewriterText,
  StaggeredText,
  CountUpText,
  GlitchText,
  HighlightText,
  RevealText,
  WaveText,
  PulseText,
  SplitText,
  ScrambleText,
  BounceInText,
} from "./AnimatedText";

// ─────────────────────────────────────────────────────────────
// IMAGE EFFECTS & TRANSFORMS
// ─────────────────────────────────────────────────────────────

export { 
  KenBurns, 
  FocusZoom, 
  ParallaxImage,
  KeyframePan,
  CinematicPan,
  RevealImage,
  SplitScreen,
} from "./KenBurns";

// ─────────────────────────────────────────────────────────────
// DEVICE MOCKUPS
// ─────────────────────────────────────────────────────────────

export { DeviceFrame, FloatingDevice, RotatingDevice } from "./DeviceFrame";

// ─────────────────────────────────────────────────────────────
// AUDIO COMPONENTS
// ─────────────────────────────────────────────────────────────

export {
  BackgroundMusic,
  SoundEffect,
  VoiceOver,
  DynamicVolume,
  AudioDucker,
} from "./AudioTrack";

// ─────────────────────────────────────────────────────────────
// BACKGROUNDS
// ─────────────────────────────────────────────────────────────

export {
  GradientBackground,
  GlowingOrb,
  OrbsBackground,
  GridBackground,
  NoiseBackground,
  RadialGradientBackground,
  MeshGradientBackground,
  AuroraBackground,
  ParticlesBackground,
} from "./Background";

// ─────────────────────────────────────────────────────────────
// CALLOUTS & CONNECTORS
// ─────────────────────────────────────────────────────────────

export { 
  ConnectorLine,
  CalloutLine,
  PathDraw,
} from "./ConnectorLine";

// ─────────────────────────────────────────────────────────────
// BUTTONS, SHAPES & CTA
// ─────────────────────────────────────────────────────────────

export { 
  ButtonLayer,
  PillBadge,
  ShapeLayer,
  CardLayer,
} from "./ButtonLayer";

// ─────────────────────────────────────────────────────────────
// EASING & ANIMATION UTILITIES
// ─────────────────────────────────────────────────────────────

export {
  // Spring configs
  SPRING_CONFIGS,
  // Bezier presets
  BEZIER_PRESETS,
  // Continuous motion presets
  CONTINUOUS_MOTION_PRESETS,
  // Shadow presets
  SHADOW_PRESETS,
  
  // Functions
  getEasingFromString,
  getStaggerDelay,
  getDurationWithVariance,
  getContinuousMotionValues,
  parseBezierString,
  createBezierEasing,
  msToFrames,
  framesToMs,
  getDefaultExitDuration,
  generateMultiLayerShadow,
} from "../lib/easing";

// Re-export types
export type { 
  AnimationFeel,
  SpringConfig,
  ContinuousMotionConfig,
  BezierPreset,
  ShadowLayer,
} from "../lib/easing";
