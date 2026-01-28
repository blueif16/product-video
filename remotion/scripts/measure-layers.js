/**
 * Layer Measurement Script
 * 
 * Reads layers JSON, computes bounding boxes for all layers using:
 * - Text width estimation with Inter font metrics
 * - Device frame dimension constants
 * - Image scaling calculations
 * 
 * Usage:
 *   node measure-layers.js <layers-json-path>
 * 
 * Output: JSON with bounding box data for each layer
 * 
 * NOTE: This script uses estimation, not actual font rendering.
 * The Python fallback in draft_tools.py is the backup.
 */

import fs from 'fs';

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const CANVAS_WIDTH = 1920;
const CANVAS_HEIGHT = 1080;

// Safe zone (12% margins)
const SAFE_ZONE = {
  left: Math.round(CANVAS_WIDTH * 0.12),    // 230
  right: Math.round(CANVAS_WIDTH * 0.88),   // 1690
  top: Math.round(CANVAS_HEIGHT * 0.12),    // 130
  bottom: Math.round(CANVAS_HEIGHT * 0.88), // 950
};

// Device frame dimensions (from theme.ts)
const DEVICE_FRAMES = {
  iphone: {
    width: 375,
    height: 812,
    defaultScale: 0.8,
  },
  iphonePro: {
    width: 393,
    height: 852,
    defaultScale: 0.8,
  },
  macbook: {
    width: 1200,
    height: 750,
    defaultScale: 0.6,
  },
  ipad: {
    width: 820,
    height: 1180,
    defaultScale: 0.55,
  },
};

// Inter font metrics - calibrated character width ratios by weight
// These are empirically derived from actual Inter font measurements
const CHAR_WIDTH_RATIOS = {
  400: 0.52,  // regular
  500: 0.53,  // medium
  600: 0.54,  // semibold
  700: 0.55,  // bold
  800: 0.56,  // extrabold
};

// ─────────────────────────────────────────────────────────────
// Text Measurement (estimation-based)
// ─────────────────────────────────────────────────────────────

/**
 * Estimate text dimensions using Inter font metrics
 */
function measureText(content, style) {
  const fontSize = style.fontSize || 48;
  const fontWeight = style.fontWeight || 400;
  const lineHeight = style.lineHeight || 1.2;
  const maxWidth = style.maxWidth;
  
  // Get character width ratio based on font weight
  const charWidthRatio = CHAR_WIDTH_RATIOS[fontWeight] || CHAR_WIDTH_RATIOS[400];
  
  // Calculate base text width
  // Add slight padding for kerning and edge characters
  const baseWidth = content.length * fontSize * charWidthRatio;
  const textWidth = Math.ceil(baseWidth * 1.05); // 5% safety margin
  
  // Height estimation for single line
  const textHeight = Math.ceil(fontSize * lineHeight);
  
  // Handle maxWidth constraint
  let finalWidth = textWidth;
  let finalHeight = textHeight;
  
  if (maxWidth && textWidth > maxWidth) {
    // Text will wrap - estimate line count
    const lineCount = Math.ceil(textWidth / maxWidth);
    finalWidth = Math.min(textWidth, maxWidth);
    finalHeight = textHeight * lineCount;
  }
  
  return { width: finalWidth, height: finalHeight };
}

/**
 * Calculate bounding box for text layer
 */
function calculateTextBbox(layer) {
  const { content, style, position, startFrame, durationFrames } = layer;
  
  const { width, height } = measureText(content, style);
  const anchor = position?.anchor || 'center';
  
  let x, y;
  
  // Handle presets
  if (position?.preset) {
    const preset = position.preset.replace(/-/g, '_');
    switch (preset) {
      case 'center':
        x = CANVAS_WIDTH / 2;
        y = CANVAS_HEIGHT / 2;
        break;
      case 'top':
        x = CANVAS_WIDTH / 2;
        y = SAFE_ZONE.top + height / 2;
        break;
      case 'bottom':
        x = CANVAS_WIDTH / 2;
        y = SAFE_ZONE.bottom - height / 2;
        break;
      case 'top_left':
        x = SAFE_ZONE.left + width / 2;
        y = SAFE_ZONE.top + height / 2;
        break;
      case 'top_right':
        x = SAFE_ZONE.right - width / 2;
        y = SAFE_ZONE.top + height / 2;
        break;
      case 'bottom_left':
        x = SAFE_ZONE.left + width / 2;
        y = SAFE_ZONE.bottom - height / 2;
        break;
      case 'bottom_right':
        x = SAFE_ZONE.right - width / 2;
        y = SAFE_ZONE.bottom - height / 2;
        break;
      default:
        x = CANVAS_WIDTH / 2;
        y = CANVAS_HEIGHT / 2;
    }
  } else {
    // Percentage coordinates
    x = (position?.x ?? 50) / 100 * CANVAS_WIDTH;
    y = (position?.y ?? 50) / 100 * CANVAS_HEIGHT;
  }
  
  // Calculate bounds based on anchor
  let left, top, right, bottom;
  
  switch (anchor) {
    case 'center':
      left = x - width / 2;
      top = y - height / 2;
      break;
    case 'top-left':
      left = x;
      top = y;
      break;
    case 'top-right':
      left = x - width;
      top = y;
      break;
    case 'bottom-left':
      left = x;
      top = y - height;
      break;
    case 'bottom-right':
      left = x - width;
      top = y - height;
      break;
    default:
      left = x - width / 2;
      top = y - height / 2;
  }
  
  right = left + width;
  bottom = top + height;
  
  return {
    width: Math.round(width),
    height: Math.round(height),
    left: Math.round(left),
    top: Math.round(top),
    right: Math.round(right),
    bottom: Math.round(bottom),
    centerX: Math.round(x),
    centerY: Math.round(y),
  };
}

/**
 * Calculate bounding box for image layer
 */
function calculateImageBbox(layer) {
  const { position, scale, device } = layer;
  
  let width, height;
  
  if (device && device !== 'none' && DEVICE_FRAMES[device]) {
    // Device frame
    const deviceConfig = DEVICE_FRAMES[device];
    const deviceScale = scale ?? deviceConfig.defaultScale;
    width = deviceConfig.width * deviceScale;
    height = deviceConfig.height * deviceScale;
  } else {
    // Regular image - assume fit to canvas if no scale
    const imgScale = scale ?? 1.0;
    // Without knowing actual image dimensions, assume 16:9 aspect ratio
    width = CANVAS_WIDTH * imgScale;
    height = CANVAS_HEIGHT * imgScale;
  }
  
  const anchor = position?.anchor || 'center';
  
  // Position
  let x = (position?.x ?? 50) / 100 * CANVAS_WIDTH;
  let y = (position?.y ?? 50) / 100 * CANVAS_HEIGHT;
  
  // Calculate bounds based on anchor
  let left, top, right, bottom;
  
  switch (anchor) {
    case 'center':
      left = x - width / 2;
      top = y - height / 2;
      break;
    case 'top-left':
      left = x;
      top = y;
      break;
    case 'top-right':
      left = x - width;
      top = y;
      break;
    case 'bottom-left':
      left = x;
      top = y - height;
      break;
    case 'bottom-right':
      left = x - width;
      top = y - height;
      break;
    default:
      left = x - width / 2;
      top = y - height / 2;
  }
  
  right = left + width;
  bottom = top + height;
  
  return {
    width: Math.round(width),
    height: Math.round(height),
    left: Math.round(left),
    top: Math.round(top),
    right: Math.round(right),
    bottom: Math.round(bottom),
    centerX: Math.round(x),
    centerY: Math.round(y),
  };
}

/**
 * Calculate bounding box for button layer
 */
function calculateButtonBbox(layer) {
  const width = layer.width || 200;
  const height = layer.height || 50;
  const x = (layer.x ?? 50) / 100 * CANVAS_WIDTH;
  const y = (layer.y ?? 50) / 100 * CANVAS_HEIGHT;
  
  // Buttons are centered by default
  const left = x - width / 2;
  const top = y - height / 2;
  
  return {
    width: Math.round(width),
    height: Math.round(height),
    left: Math.round(left),
    top: Math.round(top),
    right: Math.round(left + width),
    bottom: Math.round(top + height),
    centerX: Math.round(x),
    centerY: Math.round(y),
  };
}

/**
 * Check if bounding box is within safe zone
 */
function checkSafeZone(bbox) {
  const issues = [];
  
  if (bbox.left < SAFE_ZONE.left) {
    issues.push({ type: 'bleed_left', value: bbox.left, limit: SAFE_ZONE.left });
  }
  if (bbox.right > SAFE_ZONE.right) {
    issues.push({ type: 'bleed_right', value: bbox.right, limit: SAFE_ZONE.right });
  }
  if (bbox.top < SAFE_ZONE.top) {
    issues.push({ type: 'bleed_top', value: bbox.top, limit: SAFE_ZONE.top });
  }
  if (bbox.bottom > SAFE_ZONE.bottom) {
    issues.push({ type: 'bleed_bottom', value: bbox.bottom, limit: SAFE_ZONE.bottom });
  }
  
  return issues;
}

/**
 * Check for overlaps between layers
 */
function checkOverlaps(layers, bboxes) {
  const issues = [];
  
  // Only check text and button layers for overlap
  const checkableIndices = layers
    .map((l, i) => ({ layer: l, index: i }))
    .filter(({ layer }) => layer.type === 'text' || layer.type === 'button')
    .map(({ index }) => index);
  
  for (let i = 0; i < checkableIndices.length; i++) {
    for (let j = i + 1; j < checkableIndices.length; j++) {
      const idxA = checkableIndices[i];
      const idxB = checkableIndices[j];
      
      const boxA = bboxes[idxA];
      const boxB = bboxes[idxB];
      
      if (!boxA || !boxB) continue;
      
      // Check if boxes overlap
      const overlapX = !(boxA.right < boxB.left || boxB.right < boxA.left);
      const overlapY = !(boxA.bottom < boxB.top || boxB.bottom < boxA.top);
      
      if (overlapX && overlapY) {
        // Calculate overlap amount
        const overlapLeft = Math.max(boxA.left, boxB.left);
        const overlapRight = Math.min(boxA.right, boxB.right);
        const overlapTop = Math.max(boxA.top, boxB.top);
        const overlapBottom = Math.min(boxA.bottom, boxB.bottom);
        
        issues.push({
          type: 'overlap',
          layerA: idxA,
          layerB: idxB,
          overlapWidth: overlapRight - overlapLeft,
          overlapHeight: overlapBottom - overlapTop,
        });
      }
    }
  }
  
  return issues;
}

/**
 * Check vertical spacing between stacked text layers
 */
function checkVerticalSpacing(layers, bboxes) {
  const issues = [];
  
  // Get text layers sorted by Y position
  const textLayers = layers
    .map((l, i) => ({ layer: l, index: i, bbox: bboxes[i] }))
    .filter(({ layer, bbox }) => layer.type === 'text' && bbox)
    .sort((a, b) => a.bbox.top - b.bbox.top);
  
  // Check spacing between consecutive text layers
  for (let i = 0; i < textLayers.length - 1; i++) {
    const current = textLayers[i];
    const next = textLayers[i + 1];
    
    // Gap between bottom of current and top of next
    const gap = next.bbox.top - current.bbox.bottom;
    
    // Minimum gap should be ~10% of text height (comfortable reading)
    const minGap = Math.max(current.bbox.height, next.bbox.height) * 0.1;
    
    if (gap < minGap && gap >= 0) {
      issues.push({
        type: 'tight_spacing',
        layerA: current.index,
        layerB: next.index,
        gap: Math.round(gap),
        minGap: Math.round(minGap),
      });
    }
  }
  
  return issues;
}

// ─────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────

function measureLayers(layers) {
  const results = {
    canvas: { width: CANVAS_WIDTH, height: CANVAS_HEIGHT },
    safeZone: SAFE_ZONE,
    layers: [],
    issues: [],
  };
  
  const bboxes = [];
  
  // Process each layer
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    let bbox = null;
    let status = 'OK';
    let layerIssues = [];
    
    switch (layer.type) {
      case 'background':
        // Backgrounds are always OK - full canvas
        const subtype = layer.orbs ? 'orbs' : 
                        layer.gradient ? 'gradient' : 
                        layer.grid ? 'grid' :
                        layer.mesh ? 'mesh' :
                        layer.aurora ? 'aurora' :
                        layer.particles ? 'particles' :
                        layer.radial ? 'radial' : 'solid';
        results.layers.push({
          index: i,
          type: 'background',
          subtype,
          status: 'OK',
          bbox: { left: 0, top: 0, right: CANVAS_WIDTH, bottom: CANVAS_HEIGHT, width: CANVAS_WIDTH, height: CANVAS_HEIGHT },
        });
        bboxes.push(null);
        continue;
        
      case 'text':
        bbox = calculateTextBbox(layer);
        layerIssues = checkSafeZone(bbox);
        break;
        
      case 'image':
      case 'generated_image':
        bbox = calculateImageBbox(layer);
        layerIssues = checkSafeZone(bbox);
        break;
        
      case 'button':
        bbox = calculateButtonBbox(layer);
        layerIssues = checkSafeZone(bbox);
        break;
        
      case 'connector':
        // Connectors: check from/to points
        const from = layer.from || { x: 0, y: 0 };
        const to = layer.to || { x: 100, y: 100 };
        const minX = Math.min(from.x, to.x) / 100 * CANVAS_WIDTH;
        const maxX = Math.max(from.x, to.x) / 100 * CANVAS_WIDTH;
        const minY = Math.min(from.y, to.y) / 100 * CANVAS_HEIGHT;
        const maxY = Math.max(from.y, to.y) / 100 * CANVAS_HEIGHT;
        bbox = {
          left: Math.round(minX),
          top: Math.round(minY),
          right: Math.round(maxX),
          bottom: Math.round(maxY),
          width: Math.round(maxX - minX),
          height: Math.round(maxY - minY),
        };
        results.layers.push({
          index: i,
          type: 'connector',
          status: 'OK',
          bbox,
        });
        bboxes.push(bbox);
        continue;
        
      default:
        bboxes.push(null);
        results.layers.push({
          index: i,
          type: layer.type,
          status: 'UNKNOWN',
        });
        continue;
    }
    
    bboxes.push(bbox);
    
    // Determine status
    if (layerIssues.length > 0) {
      status = layerIssues.some(iss => iss.type.startsWith('bleed')) ? 'BLEED' : 'WARNING';
    }
    
    // Build layer result
    const layerResult = {
      index: i,
      type: layer.type,
      status,
      bbox,
    };
    
    // Add type-specific info
    if (layer.type === 'text') {
      layerResult.content = layer.content.length > 30 ? layer.content.slice(0, 30) + '...' : layer.content;
      layerResult.fontSize = layer.style?.fontSize;
    } else if (layer.type === 'image' || layer.type === 'generated_image') {
      layerResult.device = layer.device || 'none';
      layerResult.scale = layer.scale;
    }
    
    if (layerIssues.length > 0) {
      layerResult.issues = layerIssues;
    }
    
    results.layers.push(layerResult);
  }
  
  // Check overlaps and spacing
  const overlapIssues = checkOverlaps(layers, bboxes);
  const spacingIssues = checkVerticalSpacing(layers, bboxes);
  
  results.issues = [...overlapIssues, ...spacingIssues];
  
  return results;
}

// ─────────────────────────────────────────────────────────────
// CLI Entry Point
// ─────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
if (args.length < 1) {
  console.error('Usage: node measure-layers.js <layers-json-path>');
  process.exit(1);
}

const inputPath = args[0];

try {
  const content = fs.readFileSync(inputPath, 'utf-8');
  const layers = JSON.parse(content);
  
  if (!Array.isArray(layers)) {
    throw new Error('Input must be a JSON array of layers');
  }
  
  const results = measureLayers(layers);
  console.log(JSON.stringify(results, null, 2));
  
} catch (err) {
  console.error('Error:', err.message);
  process.exit(1);
}
