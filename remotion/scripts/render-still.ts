/**
 * Render Still Script
 * 
 * Renders a single frame (thumbnail/preview image).
 * 
 * Usage:
 *   npx tsx scripts/render-still.ts --output thumbnail.png [options]
 * 
 * Options:
 *   --output       Output image path (required)
 *   --composition  Composition ID (default: Thumbnail)
 *   --frame        Frame number (default: 0)
 *   --scale        Output scale (default: 1)
 *   --props        JSON props file path
 */

import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import { createRequire } from "module";
import fs from "fs";
import path from "path";

const require = createRequire(import.meta.url);

function parseArgs(): {
  outputPath: string;
  compositionId: string;
  frame: number;
  scale: number;
  propsPath?: string;
} {
  const args = process.argv.slice(2);
  const parsed: Record<string, string> = {};

  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace("--", "");
    const value = args[i + 1];
    parsed[key] = value;
  }

  if (!parsed.output) {
    console.error("Usage: npx tsx scripts/render-still.ts --output <path>");
    process.exit(1);
  }

  return {
    outputPath: parsed.output,
    compositionId: parsed.composition || "Thumbnail",
    frame: parseInt(parsed.frame || "0", 10),
    scale: parseFloat(parsed.scale || "1"),
    propsPath: parsed.props,
  };
}

async function main() {
  const { outputPath, compositionId, frame, scale, propsPath } = parseArgs();

  console.log("\n🖼️  Remotion Still Render");
  console.log("=".repeat(50));
  console.log(`   Composition: ${compositionId}`);
  console.log(`   Frame: ${frame}`);
  console.log(`   Scale: ${scale}x`);
  console.log(`   Output: ${outputPath}`);

  // Load props
  let inputProps: Record<string, any> = {};
  if (propsPath && fs.existsSync(propsPath)) {
    const propsContent = fs.readFileSync(propsPath, "utf-8");
    inputProps = JSON.parse(propsContent);
    console.log(`   Props loaded from: ${propsPath}`);
  }

  // Ensure output directory exists
  const outputDir = path.dirname(outputPath);
  if (outputDir && !fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Bundle
  console.log("\n📦 Bundling...");
  const bundled = await bundle({
    entryPoint: require.resolve("../src/index.ts"),
    webpackOverride: (config) => config,
  });
  console.log("   ✓ Bundle complete");

  // Select composition
  console.log("\n🎯 Loading composition...");
  const composition = await selectComposition({
    serveUrl: bundled,
    id: compositionId,
    inputProps,
  });
  console.log(`   ✓ ${composition.id}: ${composition.width}x${composition.height}`);

  // Render
  console.log("\n🎥 Rendering still...");
  const startTime = Date.now();

  await renderStill({
    composition,
    serveUrl: bundled,
    output: outputPath,
    frame,
    scale,
    inputProps,
  });

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  // Get file info
  const stats = fs.statSync(outputPath);
  const sizeKB = (stats.size / 1024).toFixed(1);

  console.log("\n" + "=".repeat(50));
  console.log("✅ STILL RENDER COMPLETE");
  console.log("=".repeat(50));
  console.log(`   Output: ${path.resolve(outputPath)}`);
  console.log(`   Size: ${sizeKB} KB`);
  console.log(`   Time: ${elapsed}s`);
}

main().catch((err) => {
  console.error("\n❌ Still render failed:", err);
  process.exit(1);
});
