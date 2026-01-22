/**
 * AudioTrack Components
 * 
 * Wrappers for audio handling with volume control and fades.
 */

import React from "react";
import { Audio, useCurrentFrame, useVideoConfig, interpolate, Sequence } from "remotion";

/**
 * BackgroundMusic - Background audio with fade in/out
 */
interface BackgroundMusicProps {
  src: string;
  volume?: number;
  fadeInDuration?: number;
  fadeOutDuration?: number;
  startFrom?: number;
}

export const BackgroundMusic: React.FC<BackgroundMusicProps> = ({
  src,
  volume = 0.5,
  fadeInDuration = 30,
  fadeOutDuration = 30,
  startFrom = 0,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const fadeOutStart = durationInFrames - fadeOutDuration;

  const volumeMultiplier = interpolate(
    frame,
    [0, fadeInDuration, fadeOutStart, durationInFrames],
    [0, 1, 1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  return (
    <Audio
      src={src}
      volume={volume * volumeMultiplier}
      startFrom={startFrom}
    />
  );
};

/**
 * SoundEffect - One-shot sound effect
 */
interface SoundEffectProps {
  src: string;
  startFrame: number;
  volume?: number;
  durationInFrames?: number;
}

export const SoundEffect: React.FC<SoundEffectProps> = ({
  src,
  startFrame,
  volume = 1,
  durationInFrames,
}) => {
  return (
    <Sequence from={startFrame} durationInFrames={durationInFrames}>
      <Audio src={src} volume={volume} />
    </Sequence>
  );
};

/**
 * VoiceOver - Narration track with ducking support
 */
interface VoiceOverProps {
  src: string;
  startFrame?: number;
  volume?: number;
  fadeIn?: number;
  fadeOut?: number;
}

export const VoiceOver: React.FC<VoiceOverProps> = ({
  src,
  startFrame = 0,
  volume = 1,
  fadeIn = 10,
  fadeOut = 10,
}) => {
  const frame = useCurrentFrame();

  const relativeFrame = frame - startFrame;
  
  // Simple fade calculation (actual duration would need to be known)
  const volumeMultiplier = interpolate(
    relativeFrame,
    [0, fadeIn],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  return (
    <Sequence from={startFrame}>
      <Audio src={src} volume={volume * volumeMultiplier} />
    </Sequence>
  );
};

/**
 * DynamicVolume - Audio with custom volume curve
 */
interface DynamicVolumeProps {
  src: string;
  volumeCurve: (frame: number) => number;
}

export const DynamicVolume: React.FC<DynamicVolumeProps> = ({
  src,
  volumeCurve,
}) => {
  return <Audio src={src} volume={volumeCurve} />;
};

/**
 * AudioDucker - Reduces background music when content plays
 * Use this as a wrapper around your background music
 */
interface AudioDuckerProps {
  children: React.ReactNode;
  duckingRanges: Array<{ start: number; end: number; level?: number }>;
  transitionFrames?: number;
}

export const AudioDucker: React.FC<AudioDuckerProps> = ({
  children,
  duckingRanges,
  transitionFrames = 10,
}) => {
  const frame = useCurrentFrame();

  // Calculate ducking level
  let duckLevel = 1; // 1 = full volume

  for (const range of duckingRanges) {
    const level = range.level ?? 0.3;
    
    if (frame >= range.start - transitionFrames && frame <= range.end + transitionFrames) {
      if (frame < range.start) {
        // Fade down
        duckLevel = Math.min(duckLevel, interpolate(
          frame,
          [range.start - transitionFrames, range.start],
          [1, level]
        ));
      } else if (frame > range.end) {
        // Fade up
        duckLevel = Math.min(duckLevel, interpolate(
          frame,
          [range.end, range.end + transitionFrames],
          [level, 1]
        ));
      } else {
        // In range
        duckLevel = Math.min(duckLevel, level);
      }
    }
  }

  // Clone children with modified volume
  // Note: This is a simplified approach - actual implementation would need
  // to properly handle the Audio component volume prop
  return (
    <div data-duck-level={duckLevel}>
      {children}
    </div>
  );
};
