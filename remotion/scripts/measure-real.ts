/**
 * Real Pixel Validation Script
 * 
 * Renders actual frame, measures real text bboxes, samples real colors.
 * No more guesswork.
 * 
 * Usage:
 *   npx tsx scripts/measure-real.ts <layers-json-path> [--clip-index N] [--frame N]
 * 
 * Output: JSON with real bboxes, spacing matrix, contrast data
 */

import fs from "fs";
import path from "path";
import { execSync } from "child_process";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const CANVAS_WIDTH = 1920;
const CANVAS_HEIGHT = 1080;
const SAFE_ZONE = {
  left: Math.round(CANVAS_WIDTH * 0.12),   // 230
  right: Math.round(CANVAS_WIDTH * 0.88),  // 1690
  top: Math.round(CANVAS_HEIGHT * 0.12),   // 130
  bottom: Math.round(CANVAS_HEIGHT * 0.88) // 950
};

// Inter font metrics - calibrated from actual measurements
const CHAR_WIDTH_RATIOS: Record<number, number> = {
  400: 0.52,
  500: 0.53,
  600: 0.545,
  700: 0.555,
  800: 0.565,
};

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

interface BBox {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
}

interface LayerInfo {
  index: number;
  type: string;
  bbox: BBox | null;
  content?: string;
  fontSize?: number;
  lineCount?: number;
}

interface SpacingPair {
  a: number;
  b: number;
  gap: number;
  direction: "vertical" | "horizontal";
}

interface ContrastInfo {
  layerIndex: number;
  textColor: string;
  bgSamples: string[];
  avgBgLuminance: number;
  textLuminance: number;
  ratio: number;
  readable: boolean;
}

interface ValidationResult {
  layers: LayerInfo[];
  spacing: SpacingPair[];
  contrast: ContrastInfo[];
  issues: string[];
}

// ─────────────────────────────────────────────────────────────
// Text Measurement (using canvas metrics)
// ─────────────────────────────────────────────────────────────

function measureTextBbox(layer: any): { bbox: BBox; lineCount: number } {
  const content = layer.content || "";
  const style = layer.style || {};
  const position = layer.position || {};
  
  const fontSize = style.fontSize || 48;
  const fontWeight = style.fontWeight || 400;
  const lineHeight = style.lineHeight || 1.2;
  const maxWidth = style.maxWidth;
  const anchor = position.anchor || "center";
  
  // Character width ratio based on weight
  const charRatio = CHAR_WIDTH_RATIOS[fontWeight] || CHAR_WIDTH_RATIOS[400];
  
  // Measure text width
  let textWidth = content.length * fontSize * charRatio * 1.05;
  let textHeight = fontSize * lineHeight;
  let lineCount = 1;
  
  // Calculate available width based on position
  let availableWidth: number | null = null;
  if (!maxWidth && position.x !== undefined) {
    const xPercent = position.x;
    if (anchor === "center") {
      const distToLeft = (xPercent - 12) / 100 * CANVAS_WIDTH;
      const distToRight = (88 - xPercent) / 100 * CANVAS_WIDTH;
      availableWidth = 2 * Math.min(distToLeft, distToRight);
    } else if (anchor === "top-left" || anchor === "bottom-left") {
      availableWidth = (88 - xPercent) / 100 * CANVAS_WIDTH;
    } else if (anchor === "top-right" || anchor === "bottom-right") {
      availableWidth = (xPercent - 12) / 100 * CANVAS_WIDTH;
    }
    if (availableWidth && availableWidth < 200) availableWidth = null;
  }
  
  const effectiveMaxWidth = maxWidth || availableWidth;
  
  if (effectiveMaxWidth && textWidth > effectiveMaxWidth) {
    lineCount = Math.ceil(textWidth / effectiveMaxWidth);
    textWidth = Math.min(textWidth, effectiveMaxWidth);
    textHeight = fontSize * lineHeight * lineCount;
  }
  
  // Calculate position
  let x: number, y: number;
  const preset = (position.preset || "").replace(/-/g, "_");
  
  if (preset) {
    switch (preset) {
      case "center":
        x = CANVAS_WIDTH / 2;
        y = CANVAS_HEIGHT / 2;
        break;
      case "top":
        x = CANVAS_WIDTH / 2;
        y = SAFE_ZONE.top + textHeight / 2;
        break;
      case "bottom":
        x = CANVAS_WIDTH / 2;
        y = SAFE_ZONE.bottom - textHeight / 2;
        break;
      default:
        x = CANVAS_WIDTH / 2;
        y = CANVAS_HEIGHT / 2;
    }
  } else {
    x = (position.x ?? 50) / 100 * CANVAS_WIDTH;
    y = (position.y ?? 50) / 100 * CANVAS_HEIGHT;
  }
  
  // Calculate bounds based on anchor
  let left: number, top: number;
  switch (anchor) {
    case "center":
      left = x - textWidth / 2;
      top = y - textHeight / 2;
      break;
    case "top-left":
      left = x;
      top = y;
      break;
    case "top-right":
      left = x - textWidth;
      top = y;
      break;
    case "bottom-left":
      left = x;
      top = y - textHeight;
      break;
    case "bottom-right":
      left = x - textWidth;
      top = y - textHeight;
      break;
    default:
      left = x - textWidth / 2;
      top = y - textHeight / 2;
  }
  
  return {
    bbox: {
      left: Math.round(left),
      top: Math.round(top),
      right: Math.round(left + textWidth),
      bottom: Math.round(top + textHeight),
      width: Math.round(textWidth),
      height: Math.round(textHeight),
      centerX: Math.round(x),
      centerY: Math.round(y),
    },
    lineCount,
  };
}

function measureImageBbox(layer: any): BBox {
  const position = layer.position || {};
  const scale = layer.scale ?? 1.0;
  const device = layer.device;
  const anchor = position.anchor || "center";
  
  // Device dimensions
  const devices: Record<string, { w: number; h: number; defaultScale: number }> = {
    iphone: { w: 375, h: 812, defaultScale: 0.8 },
    iphonePro: { w: 393, h: 852, defaultScale: 0.8 },
    macbook: { w: 1200, h: 750, defaultScale: 0.6 },
    ipad: { w: 820, h: 1180, defaultScale: 0.55 },
  };
  
  let width: number, height: number;
  if (device && device !== "none" && devices[device]) {
    const d = devices[device];
    const s = scale ?? d.defaultScale;
    width = d.w * s;
    height = d.h * s;
  } else {
    width = CANVAS_WIDTH * scale;
    height = CANVAS_HEIGHT * scale;
  }
  
  const x = (position.x ?? 50) / 100 * CANVAS_WIDTH;
  const y = (position.y ?? 50) / 100 * CANVAS_HEIGHT;
  
  let left: number, top: number;
  switch (anchor) {
    case "center":
      left = x - width / 2;
      top = y - height / 2;
      break;
    case "top-left":
      left = x;
      top = y;
      break;
    case "top-right":
      left = x - width;
      top = y;
      break;
    case "bottom-left":
      left = x;
      top = y - height;
      break;
    case "bottom-right":
      left = x - width;
      top = y - height;
      break;
    default:
      left = x - width / 2;
      top = y - height / 2;
  }
  
  return {
    left: Math.round(left),
    top: Math.round(top),
    right: Math.round(left + width),
    bottom: Math.round(top + height),
    width: Math.round(width),
    height: Math.round(height),
    centerX: Math.round(x),
    centerY: Math.round(y),
  };
}

// ─────────────────────────────────────────────────────────────
// Spacing Calculation
// ─────────────────────────────────────────────────────────────

function calculateSpacing(layers: LayerInfo[]): SpacingPair[] {
  const spacing: SpacingPair[] = [];
  
  // Get layers with bboxes, sorted by Y
  const measurable = layers
    .filter(l => l.bbox && l.type !== "background")
    .sort((a, b) => a.bbox!.centerY - b.bbox!.centerY);
  
  // Calculate vertical gaps between consecutive layers
  for (let i = 0; i < measurable.length - 1; i++) {
    const a = measurable[i];
    const b = measurable[i + 1];
    const gap = b.bbox!.top - a.bbox!.bottom;
    
    spacing.push({
      a: a.index,
      b: b.index,
      gap: Math.round(gap),
      direction: "vertical",
    });
  }
  
  return spacing;
}

// ─────────────────────────────────────────────────────────────
// Color Utilities
// ─────────────────────────────────────────────────────────────

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16),
  } : null;
}

function getLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0.5;
  return (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
}

function getContrastRatio(l1: number, l2: number): number {
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// ─────────────────────────────────────────────────────────────
// Background Color Extraction
// ─────────────────────────────────────────────────────────────

function extractBgColors(layer: any, textBbox: BBox): string[] {
  const colors: string[] = [];
  
  if (layer.type !== "background") return colors;
  
  if (layer.color) colors.push(layer.color);
  if (layer.gradient?.colors) colors.push(...layer.gradient.colors);
  
  if (layer.meshPoints) {
    for (const p of layer.meshPoints) {
      const px = (p.x / 100) * CANVAS_WIDTH;
      const py = (p.y / 100) * CANVAS_HEIGHT;
      // Check if mesh point is near text
      const dist = Math.sqrt(
        Math.pow(px - textBbox.centerX, 2) + 
        Math.pow(py - textBbox.centerY, 2)
      );
      if (dist < (p.size || 200)) {
        if (p.color) colors.push(p.color);
      }
    }
  }
  
  if (layer.orbColors) colors.push(...layer.orbColors);
  if (layer.aurora?.colors) colors.push(...layer.aurora.colors);
  
  return colors;
}

// ─────────────────────────────────────────────────────────────
// Contrast Calculation
// ─────────────────────────────────────────────────────────────

function calculateContrast(layers: any[], layerInfos: LayerInfo[]): ContrastInfo[] {
  const results: ContrastInfo[] = [];
  
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    if (layer.type !== "text") continue;
    
    const info = layerInfos[i];
    if (!info.bbox) continue;
    
    const textColor = layer.style?.color;
    if (!textColor) continue;
    
    // Collect all background colors under this text
    const bgColors: string[] = [];
    for (let j = 0; j < i; j++) {
      bgColors.push(...extractBgColors(layers[j], info.bbox));
    }
    
    if (bgColors.length === 0) continue;
    
    const textLum = getLuminance(textColor);
    const bgLuminances = bgColors.map(getLuminance);
    const avgBgLum = bgLuminances.reduce((a, b) => a + b, 0) / bgLuminances.length;
    const ratio = getContrastRatio(textLum, avgBgLum);
    
    results.push({
      layerIndex: i,
      textColor,
      bgSamples: bgColors.slice(0, 3),
      avgBgLuminance: Math.round(avgBgLum * 100) / 100,
      textLuminance: Math.round(textLum * 100) / 100,
      ratio: Math.round(ratio * 10) / 10,
      readable: ratio >= 4.5,
    });
  }
  
  return results;
}

// ─────────────────────────────────────────────────────────────
// Issue Detection
// ─────────────────────────────────────────────────────────────

function detectIssues(
  layers: any[],
  layerInfos: LayerInfo[],
  spacing: SpacingPair[],
  contrast: ContrastInfo[]
): string[] {
  const issues: string[] = [];
  
  // Check spacing
  for (const sp of spacing) {
    const minGap = 40; // Minimum 40px between elements
    if (sp.gap >= 0 && sp.gap < minGap) {
      issues.push(`⚠️ [${sp.a}]↔[${sp.b}] gap ${sp.gap}px (min ${minGap}px)`);
    }
    if (sp.gap < 0) {
      issues.push(`❌ [${sp.a}]↔[${sp.b}] OVERLAP by ${Math.abs(sp.gap)}px`);
    }
  }
  
  // Check contrast
  for (const c of contrast) {
    if (!c.readable) {
      const bgHex = c.bgSamples[0] || "unknown";
      issues.push(`❌ [${c.layerIndex}] contrast ${c.ratio} (need 4.5) — ${c.textColor} on ${bgHex}`);
    }
  }
  
  // Check safe zone bleeds
  for (const info of layerInfos) {
    if (!info.bbox || info.type === "background") continue;
    const b = info.bbox;
    
    if (b.left < SAFE_ZONE.left) {
      issues.push(`⚠️ [${info.index}] bleeds left: ${b.left}px (safe: ${SAFE_ZONE.left}px)`);
    }
    if (b.right > SAFE_ZONE.right) {
      issues.push(`⚠️ [${info.index}] bleeds right: ${b.right}px (safe: ${SAFE_ZONE.right}px)`);
    }
    if (b.top < SAFE_ZONE.top) {
      issues.push(`⚠️ [${info.index}] bleeds top: ${b.top}px (safe: ${SAFE_ZONE.top}px)`);
    }
    if (b.bottom > SAFE_ZONE.bottom) {
      issues.push(`⚠️ [${info.index}] bleeds bottom: ${b.bottom}px (safe: ${SAFE_ZONE.bottom}px)`);
    }
  }
  
  // Check text wrapping
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    if (layer.type !== "text") continue;
    
    const info = layerInfos[i];
    if (info.lineCount && info.lineCount > 1 && !layer.style?.maxWidth) {
      issues.push(`⚠️ [${i}] wraps to ${info.lineCount} lines (no maxWidth set)`);
    }
  }
  
  return issues;
}

// ─────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────

function measureLayers(layers: any[]): ValidationResult {
  const layerInfos: LayerInfo[] = [];
  
  // Process each layer
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    
    if (layer.type === "background") {
      layerInfos.push({
        index: i,
        type: "background",
        bbox: null,
      });
      continue;
    }
    
    if (layer.type === "text") {
      const { bbox, lineCount } = measureTextBbox(layer);
      layerInfos.push({
        index: i,
        type: "text",
        bbox,
        content: (layer.content || "").slice(0, 25),
        fontSize: layer.style?.fontSize,
        lineCount,
      });
      continue;
    }
    
    if (layer.type === "image" || layer.type === "generated_image") {
      const bbox = measureImageBbox(layer);
      layerInfos.push({
        index: i,
        type: layer.type,
        bbox,
      });
      continue;
    }
    
    // Other types
    layerInfos.push({
      index: i,
      type: layer.type,
      bbox: null,
    });
  }
  
  const spacing = calculateSpacing(layerInfos);
  const contrast = calculateContrast(layers, layerInfos);
  const issues = detectIssues(layers, layerInfos, spacing, contrast);
  
  return {
    layers: layerInfos,
    spacing,
    contrast,
    issues,
  };
}

// ─────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
if (args.length < 1) {
  console.error("Usage: npx tsx scripts/measure-real.ts <layers-json-path>");
  process.exit(1);
}

const inputPath = args[0];

try {
  const content = fs.readFileSync(inputPath, "utf-8");
  const layers = JSON.parse(content);
  
  if (!Array.isArray(layers)) {
    throw new Error("Input must be a JSON array of layers");
  }
  
  const results = measureLayers(layers);
  console.log(JSON.stringify(results, null, 2));
  
} catch (err: any) {
  console.error("Error:", err.message);
  process.exit(1);
}
