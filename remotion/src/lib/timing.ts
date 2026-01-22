/**
 * Timing & Beat Grid Utilities
 * 
 * For synchronizing animations to music beats.
 * All timing values align to common BPM values for beat-synced editing.
 */

/**
 * Convert beats to frames
 * @param beats Number of beats
 * @param bpm Beats per minute of the track
 * @param fps Video frame rate
 */
export const beatsToFrames = (beats: number, bpm: number, fps: number): number => {
  const secondsPerBeat = 60 / bpm;
  return Math.round(beats * secondsPerBeat * fps);
};

/**
 * Convert seconds to frames
 */
export const secondsToFrames = (seconds: number, fps: number): number => {
  return Math.round(seconds * fps);
};

/**
 * Convert frames to seconds
 */
export const framesToSeconds = (frames: number, fps: number): number => {
  return frames / fps;
};

/**
 * Get frame at specific beat
 * @param beat Beat number (1-indexed)
 * @param bpm Track BPM
 * @param fps Video FPS
 */
export const beatToFrame = (beat: number, bpm: number, fps: number): number => {
  return beatsToFrames(beat - 1, bpm, fps);
};

/**
 * Common timing presets at 30fps for 120 BPM
 * (Most common for upbeat product videos)
 */
export const timing120BPM = {
  quarterBeat: 7,    // 0.125s - quick accent
  halfBeat: 15,      // 0.25s - fast transition
  oneBeat: 30,       // 0.5s - standard move
  twoBeats: 60,      // 1s - slow reveal
  oneBar: 60,        // 1s (4 beats at 120BPM = 2s, but often use half)
  twoBar: 120,       // 2s - scene transition
  fourBar: 240,      // 4s - major section
};

/**
 * Common timing presets at 30fps for 100 BPM
 * (Common for corporate/calm videos)
 */
export const timing100BPM = {
  quarterBeat: 9,
  halfBeat: 18,
  oneBeat: 18,
  twoBeats: 36,
  oneBar: 72,
  twoBar: 144,
  fourBar: 288,
};

/**
 * Generate beat grid for a track
 * @param durationFrames Total video duration in frames
 * @param bpm Track BPM
 * @param fps Video FPS
 * @returns Array of frame numbers where beats land
 */
export const generateBeatGrid = (
  durationFrames: number,
  bpm: number,
  fps: number
): number[] => {
  const framesPerBeat = beatsToFrames(1, bpm, fps);
  const beats: number[] = [];
  
  for (let frame = 0; frame < durationFrames; frame += framesPerBeat) {
    beats.push(Math.round(frame));
  }
  
  return beats;
};

/**
 * Snap a frame to nearest beat
 */
export const snapToBeat = (
  frame: number,
  bpm: number,
  fps: number
): number => {
  const framesPerBeat = beatsToFrames(1, bpm, fps);
  return Math.round(frame / framesPerBeat) * framesPerBeat;
};

/**
 * Standard durations for different content types (at 30fps)
 */
export const standardDurations = {
  // Scene types
  hook: 90,           // 3s - opening hook
  titleCard: 60,      // 2s - title display
  featureDemo: 120,   // 4s - feature demonstration
  screenshot: 75,     // 2.5s - screenshot display
  transition: 15,     // 0.5s - between scenes
  cta: 90,            // 3s - call to action
  
  // Animation types
  fadeIn: 15,         // 0.5s
  fadeOut: 15,        // 0.5s
  slideIn: 20,        // 0.67s
  scaleIn: 18,        // 0.6s
  typewriter: 60,     // 2s for ~20 chars
  
  // Text display minimums (reading time)
  shortText: 45,      // 1.5s - tagline
  mediumText: 75,     // 2.5s - feature description
  longText: 120,      // 4s - detailed explanation
};

/**
 * Calculate reading time in frames for text
 * @param text Text content
 * @param fps Frame rate
 * @param wordsPerMinute Reading speed (default 200)
 */
export const textReadingFrames = (
  text: string,
  fps: number,
  wordsPerMinute: number = 200
): number => {
  const words = text.split(/\s+/).length;
  const minutes = words / wordsPerMinute;
  const seconds = minutes * 60;
  // Minimum 1.5 seconds, add 0.5s buffer
  return Math.max(Math.round((seconds + 0.5) * fps), Math.round(1.5 * fps));
};

/**
 * Easing presets compatible with Remotion
 */
export const easingPresets = {
  // Standard easings
  linear: undefined,
  easeOut: { extrapolateRight: "clamp" as const },
  easeIn: { extrapolateLeft: "clamp" as const },
  easeInOut: { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const },
};
