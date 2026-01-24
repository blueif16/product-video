/**
 * Centralized Design Tokens
 * 
 * All colors, fonts, spacing used across compositions.
 * Ensures visual consistency throughout videos.
 * 
 * Supports BOTH light and dark themes for app-matching videos.
 */

export const theme = {
  colors: {
    // Dark theme backgrounds (default)
    background: "#0f172a",
    backgroundDark: "#020617",
    backgroundLight: "#1e293b",
    
    // Light theme backgrounds
    backgroundCream: "#faf5ef",
    backgroundWhite: "#ffffff",
    backgroundLightGray: "#f5f5f5",
    backgroundWarm: "#fefcf9",
    
    // Brand (works on both themes)
    primary: "#6366f1",
    primaryLight: "#818cf8",
    primaryDark: "#4f46e5",
    
    // Accents
    accent: "#ec4899",
    accentAlt: "#06b6d4",
    success: "#22c55e",
    warning: "#f59e0b",
    
    // Text for dark backgrounds
    text: "#ffffff",
    textMuted: "#94a3b8",
    textDark: "#64748b",
    
    // Text for light backgrounds
    textOnLight: "#1a1a1a",
    textMutedOnLight: "#4a5568",
    textDarkOnLight: "#2d3748",
    
    // Overlays
    overlayDark: "rgba(0, 0, 0, 0.6)",
    overlayLight: "rgba(255, 255, 255, 0.1)",
    overlayOnLight: "rgba(0, 0, 0, 0.05)",
  },
  
  fonts: {
    heading: "Inter",
    body: "Inter",
    mono: "JetBrains Mono, monospace",
  },
  
  fontSizes: {
    hero: 120,
    title: 80,
    subtitle: 48,
    heading: 36,
    body: 24,
    caption: 18,
    small: 14,
  },
  
  fontWeights: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  },
  
  spacing: {
    safe: 96,        // 5% of 1920px - safe zone from edges
    xs: 8,
    sm: 16,
    md: 24,
    lg: 40,
    xl: 60,
    xxl: 100,
  },
  
  shadows: {
    // For dark backgrounds
    small: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
    medium: "0 10px 15px -3px rgba(0, 0, 0, 0.2)",
    large: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
    glow: (color: string) => `0 0 80px ${color}80`,
    
    // For light backgrounds (softer)
    smallLight: "0 2px 4px rgba(0, 0, 0, 0.05)",
    mediumLight: "0 4px 12px rgba(0, 0, 0, 0.08)",
    largeLight: "0 12px 40px rgba(0, 0, 0, 0.12)",
    subtleGlow: (color: string) => `0 0 40px ${color}40`,
  },
  
  gradients: {
    // Dark theme gradients
    primary: "linear-gradient(135deg, #6366f1 0%, #ec4899 100%)",
    dark: "linear-gradient(180deg, #0f172a 0%, #020617 100%)",
    radialGlow: (color: string) => `radial-gradient(circle, ${color}40 0%, transparent 70%)`,
    
    // Light theme gradients
    warmLight: "linear-gradient(180deg, #faf5ef 0%, #f0e6d8 100%)",
    softLight: "linear-gradient(180deg, #ffffff 0%, #f5f5f5 100%)",
    creamToWhite: "linear-gradient(180deg, #fefcf9 0%, #ffffff 100%)",
  },
  
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 16,
    xl: 24,
    full: 9999,
  },
  
  // Device frame dimensions
  devices: {
    iphone: {
      width: 375,
      height: 812,
      borderRadius: 40,
      bezelWidth: 12,
    },
    iphonePro: {
      width: 393,
      height: 852,
      borderRadius: 55,
      bezelWidth: 12,
    },
    macbook: {
      width: 1200,
      height: 750,
      borderRadius: 12,
      bezelWidth: 16,
      chinHeight: 40,
    },
    ipad: {
      width: 820,
      height: 1180,
      borderRadius: 24,
      bezelWidth: 20,
    },
  },
} as const;

// Helper functions for dynamic theme selection
export const getBackgroundColor = (isLight: boolean): string => {
  return isLight ? theme.colors.backgroundCream : theme.colors.backgroundDark;
};

export const getTextColor = (isLight: boolean): string => {
  return isLight ? theme.colors.textOnLight : theme.colors.text;
};

export const getTextShadow = (isLight: boolean, color?: string): string => {
  if (isLight) {
    return "0 2px 8px rgba(0, 0, 0, 0.1)";
  }
  return color 
    ? `0 4px 30px ${color}80` 
    : "0 4px 30px rgba(0, 0, 0, 0.5)";
};

// Type exports
export type ThemeColors = keyof typeof theme.colors;
export type ThemeFontSizes = keyof typeof theme.fontSizes;
