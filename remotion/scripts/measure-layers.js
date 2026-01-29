/**
 * Layer Measurement Script (Fallback)
 * 
 * Estimation-based measurement. Used when measure-real.ts fails.
 * Matches the same output format as measure-real.ts.
 * 
 * Usage:
 *   node measure-layers.js <layers-json-path>
 */

import fs from 'fs';

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const CANVAS_WIDTH = 1920;
const CANVAS_HEIGHT = 1080;

const SAFE_ZONE = {
  left: Math.round(CANVAS_WIDTH * 0.12),
  right: Math.round(CANVAS_WIDTH * 0.88),
  top: Math.round(CANVAS_HEIGHT * 0.12),
  bottom: Math.round(CANVAS_HEIGHT * 0.88),
};

const MIN_SPACING = 40;

const CHAR_WIDTH_RATIOS = {
  400: 0.52,
  500: 0.53,
  600: 0.545,
  700: 0.555,
  800: 0.565,
};

const DEVICE_FRAMES = {
  iphone: { width: 375, height: 812, defaultScale: 0.8 },
  iphonePro: { width: 393, height: 852, defaultScale: 0.8 },
  macbook: { width: 1200, height: 750, defaultScale: 0.6 },
  ipad: { width: 820, height: 1180, defaultScale: 0.55 },
};

// ─────────────────────────────────────────────────────────────
// Text Measurement
// ─────────────────────────────────────────────────────────────

function measureTextBbox(layer) {
  const content = layer.content || '';
  const style = layer.style || {};
  const position = layer.position || {};
  
  const fontSize = style.fontSize || 48;
  const fontWeight = style.fontWeight || 400;
  const lineHeight = style.lineHeight || 1.2;
  const maxWidth = style.maxWidth;
  const anchor = position.anchor || 'center';
  
  const charRatio = CHAR_WIDTH_RATIOS[fontWeight] || CHAR_WIDTH_RATIOS[400];
  
  let textWidth = content.length * fontSize * charRatio * 1.05;
  let textHeight = fontSize * lineHeight;
  let lineCount = 1;
  
  // Available width based on position
  let availableWidth = null;
  if (!maxWidth && position.x !== undefined) {
    const xPercent = position.x;
    if (anchor === 'center') {
      const distToLeft = (xPercent - 12) / 100 * CANVAS_WIDTH;
      const distToRight = (88 - xPercent) / 100 * CANVAS_WIDTH;
      availableWidth = 2 * Math.min(distToLeft, distToRight);
    } else if (anchor === 'top-left' || anchor === 'bottom-left') {
      availableWidth = (88 - xPercent) / 100 * CANVAS_WIDTH;
    } else if (anchor === 'top-right' || anchor === 'bottom-right') {
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
  
  // Position
  let x, y;
  const preset = (position.preset || '').replace(/-/g, '_');
  
  if (preset) {
    switch (preset) {
      case 'center':
        x = CANVAS_WIDTH / 2;
        y = CANVAS_HEIGHT / 2;
        break;
      case 'top':
        x = CANVAS_WIDTH / 2;
        y = SAFE_ZONE.top + textHeight / 2;
        break;
      case 'bottom':
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
  
  // Bounds from anchor
  let left, top;
  switch (anchor) {
    case 'center':
      left = x - textWidth / 2;
      top = y - textHeight / 2;
      break;
    case 'top-left':
      left = x; top = y;
      break;
    case 'top-right':
      left = x - textWidth; top = y;
      break;
    case 'bottom-left':
      left = x; top = y - textHeight;
      break;
    case 'bottom-right':
      left = x - textWidth; top = y - textHeight;
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

function measureImageBbox(layer) {
  const position = layer.position || {};
  const scale = layer.scale ?? 1.0;
  const device = layer.device;
  const anchor = position.anchor || 'center';
  
  let width, height;
  if (device && device !== 'none' && DEVICE_FRAMES[device]) {
    const d = DEVICE_FRAMES[device];
    const s = scale ?? d.defaultScale;
    width = d.width * s;
    height = d.height * s;
  } else {
    width = CANVAS_WIDTH * scale;
    height = CANVAS_HEIGHT * scale;
  }
  
  const x = (position.x ?? 50) / 100 * CANVAS_WIDTH;
  const y = (position.y ?? 50) / 100 * CANVAS_HEIGHT;
  
  let left, top;
  switch (anchor) {
    case 'center':
      left = x - width / 2; top = y - height / 2;
      break;
    case 'top-left':
      left = x; top = y;
      break;
    case 'top-right':
      left = x - width; top = y;
      break;
    case 'bottom-left':
      left = x; top = y - height;
      break;
    case 'bottom-right':
      left = x - width; top = y - height;
      break;
    default:
      left = x - width / 2; top = y - height / 2;
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
// Color Utilities
// ─────────────────────────────────────────────────────────────

function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16),
  } : null;
}

function getLuminance(hex) {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0.5;
  return (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
}

function getContrastRatio(l1, l2) {
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function extractBgColors(layer, textBbox) {
  const colors = [];
  if (layer.type !== 'background') return colors;
  
  if (layer.color) colors.push(layer.color);
  if (layer.gradient?.colors) colors.push(...layer.gradient.colors);
  if (layer.meshPoints) {
    for (const p of layer.meshPoints) {
      const px = (p.x / 100) * CANVAS_WIDTH;
      const py = (p.y / 100) * CANVAS_HEIGHT;
      const dist = Math.sqrt(Math.pow(px - textBbox.centerX, 2) + Math.pow(py - textBbox.centerY, 2));
      if (dist < (p.size || 200) && p.color) colors.push(p.color);
    }
  }
  if (layer.orbColors) colors.push(...layer.orbColors);
  
  return colors;
}

// ─────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────

function measureLayers(layers) {
  const layerInfos = [];
  
  // Process layers
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    
    if (layer.type === 'background') {
      layerInfos.push({ index: i, type: 'background', bbox: null });
      continue;
    }
    
    if (layer.type === 'text') {
      const { bbox, lineCount } = measureTextBbox(layer);
      layerInfos.push({
        index: i,
        type: 'text',
        bbox,
        content: (layer.content || '').slice(0, 25),
        fontSize: layer.style?.fontSize,
        lineCount,
      });
      continue;
    }
    
    if (layer.type === 'image' || layer.type === 'generated_image') {
      const bbox = measureImageBbox(layer);
      layerInfos.push({ index: i, type: layer.type, bbox });
      continue;
    }
    
    layerInfos.push({ index: i, type: layer.type, bbox: null });
  }
  
  // Spacing
  const spacing = [];
  const measurable = layerInfos
    .filter(l => l.bbox && l.type !== 'background')
    .sort((a, b) => a.bbox.centerY - b.bbox.centerY);
  
  for (let i = 0; i < measurable.length - 1; i++) {
    const a = measurable[i];
    const b = measurable[i + 1];
    spacing.push({
      a: a.index,
      b: b.index,
      gap: Math.round(b.bbox.top - a.bbox.bottom),
      direction: 'vertical',
    });
  }
  
  // Contrast
  const contrast = [];
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    if (layer.type !== 'text') continue;
    
    const info = layerInfos[i];
    if (!info.bbox) continue;
    
    const textColor = layer.style?.color;
    if (!textColor) continue;
    
    const bgColors = [];
    for (let j = 0; j < i; j++) {
      bgColors.push(...extractBgColors(layers[j], info.bbox));
    }
    
    if (bgColors.length === 0) continue;
    
    const textLum = getLuminance(textColor);
    const bgLums = bgColors.map(getLuminance);
    const avgBgLum = bgLums.reduce((a, b) => a + b, 0) / bgLums.length;
    const ratio = getContrastRatio(textLum, avgBgLum);
    
    contrast.push({
      layerIndex: i,
      textColor,
      bgSamples: bgColors.slice(0, 3),
      avgBgLuminance: Math.round(avgBgLum * 100) / 100,
      textLuminance: Math.round(textLum * 100) / 100,
      ratio: Math.round(ratio * 10) / 10,
      readable: ratio >= 4.5,
    });
  }
  
  // Issues
  const issues = [];
  
  for (const sp of spacing) {
    if (sp.gap < 0) {
      issues.push(`❌ [${sp.a}]↔[${sp.b}] OVERLAP by ${Math.abs(sp.gap)}px`);
    } else if (sp.gap < MIN_SPACING) {
      issues.push(`⚠️ [${sp.a}]↔[${sp.b}] gap ${sp.gap}px (min ${MIN_SPACING}px)`);
    }
  }
  
  for (const c of contrast) {
    if (!c.readable) {
      const bg = c.bgSamples[0] || '?';
      issues.push(`❌ [${c.layerIndex}] contrast ${c.ratio} (need 4.5) — ${c.textColor} on ${bg}`);
    }
  }
  
  for (const info of layerInfos) {
    if (!info.bbox || info.type === 'background') continue;
    const b = info.bbox;
    
    if (b.left < SAFE_ZONE.left) issues.push(`⚠️ [${info.index}] bleeds left`);
    if (b.right > SAFE_ZONE.right) issues.push(`⚠️ [${info.index}] bleeds right`);
    if (b.top < SAFE_ZONE.top) issues.push(`⚠️ [${info.index}] bleeds top`);
    if (b.bottom > SAFE_ZONE.bottom) issues.push(`⚠️ [${info.index}] bleeds bottom`);
  }
  
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    if (layer.type !== 'text') continue;
    const info = layerInfos[i];
    if (info.lineCount > 1 && !layer.style?.maxWidth) {
      issues.push(`⚠️ [${i}] wraps to ${info.lineCount} lines (no maxWidth)`);
    }
  }
  
  return { layers: layerInfos, spacing, contrast, issues };
}

// ─────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
if (args.length < 1) {
  console.error('Usage: node measure-layers.js <layers-json-path>');
  process.exit(1);
}

try {
  const content = fs.readFileSync(args[0], 'utf-8');
  const layers = JSON.parse(content);
  
  if (!Array.isArray(layers)) {
    throw new Error('Input must be a JSON array');
  }
  
  const results = measureLayers(layers);
  console.log(JSON.stringify(results, null, 2));
  
} catch (err) {
  console.error('Error:', err.message);
  process.exit(1);
}
