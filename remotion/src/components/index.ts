// Animation wrappers
export { FadeIn, FadeInOut } from "./FadeIn";
export { SlideIn, SlideUp, SlideDown, SlideLeft, SlideRight } from "./SlideIn";
export { ScaleIn, PopIn, ZoomIn } from "./ScaleIn";

// Text animations
export {
  TypewriterText,
  StaggeredText,
  CountUpText,
  GlitchText,
  HighlightText,
  RevealText,
  WaveText,
} from "./AnimatedText";

// Image effects
export { KenBurns, FocusZoom, ParallaxImage } from "./KenBurns";

// Device mockups
export { DeviceFrame, FloatingDevice, RotatingDevice } from "./DeviceFrame";

// Audio
export {
  BackgroundMusic,
  SoundEffect,
  VoiceOver,
  DynamicVolume,
  AudioDucker,
} from "./AudioTrack";

// Backgrounds
export {
  GradientBackground,
  GlowingOrb,
  OrbsBackground,
  GridBackground,
  NoiseBackground,
  RadialGradientBackground,
} from "./Background";

// Spring physics presets (for direct use)
export const SPRING_CONFIGS = {
  snappy: { damping: 25, stiffness: 400, mass: 0.3 },
  smooth: { damping: 20, stiffness: 150, mass: 0.5 },
  bouncy: { damping: 8, stiffness: 200, mass: 0.5 },
} as const;

export type AnimationFeel = keyof typeof SPRING_CONFIGS;
