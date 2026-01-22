/**
 * Remotion Render Script
 * 
 * Called by Python render_client.py to render videos.
 * 
 * Usage:
 *   npx tsx scripts/render.ts --spec <path> --output <path> [options]
 * 
 * Options:
 *   --spec         Path to VideoSpec JSON file
 *   --output       Output video path
 *   --composition  Composition ID (default: ProductVideo)
 *   --codec        Video codec (default: h264)
 *   --crf          Quality (0-51, default: 18)
 */

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { createRequire } from "module";
import fs from "fs";
import path from "path";

const require = createRequire(import.meta.url);

// Parse command line arguments
function parseArgs(): {
  specPath: string;
  outputPath: string;
  compositionId: string;
  codec: "h264" | "h265" | "vp8" | "vp9" | "prores";
  crf: number;
} {
  const args = process.argv.slice(2);
  const parsed: Record<string, string> = {};
  
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace("--", "");
    const value = args[i + 1];
    parsed[key] = value;
  }
  
  if (!parsed.spec || !parsed.output) {
    console.error("Usage: npx tsx scripts/render.ts --spec <path> --output <path>");
    process.exit(1);
  }
  
  return {
    specPath: parsed.spec,
    outputPath: parsed.output,
    compositionId: parsed.composition || "ProductVideo",
    codec: (parsed.codec as any) || "h264",
    crf: parseInt(parsed.crf || "18", 10),
  };
}

async function main() {
  const { specPath, outputPath, compositionId, codec, crf } = parseArgs();
  
  console.log("\n🎬 Remotion Render Starting...");
  console.log(`   Composition: ${compositionId}`);
  console.log(`   Spec: ${specPath}`);
  console.log(`   Output: ${outputPath}`);
  console.log(`   Codec: ${codec}, CRF: ${crf}`);
  
  // Read spec
  let inputProps: Record<string, any> = {};
  if (fs.existsSync(specPath)) {
    const specContent = fs.readFileSync(specPath, "utf-8");
    inputProps = JSON.parse(specContent);
    console.log(`   Props loaded: ${Object.keys(inputProps).length} keys`);
  } else {
    console.warn(`   ⚠️  Spec file not found, using default props`);
  }
  
  // Ensure output directory exists
  const outputDir = path.dirname(outputPath);
  if (!fs.existsSync(outputDir)) {
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
  console.log("\n🎯 Selecting composition...");
  const composition = await selectComposition({
    serveUrl: bundled,
    id: compositionId,
    inputProps,
  });
  console.log(`   ✓ ${composition.id}: ${composition.durationInFrames} frames @ ${composition.fps}fps`);
  
  // Render
  console.log("\n🎥 Rendering...");
  const startTime = Date.now();
  
  await renderMedia({
    composition,
    serveUrl: bundled,
    codec,
    outputLocation: outputPath,
    inputProps,
    crf,
    onProgress: ({ progress }) => {
      const percent = Math.round(progress * 100);
      process.stdout.write(`\r   Progress: ${percent}%`);
    },
    chromiumOptions: {
      enableMultiProcessOnLinux: true,
    },
  });
  
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`\n\n✅ Render complete in ${elapsed}s`);
  console.log(`   Output: ${outputPath}`);
}

main().catch((err) => {
  console.error("\n❌ Render failed:", err);
  process.exit(1);
});
