/**
 * Remotion Test Render Script
 * 
 * Renders the TestTextAnimations composition to verify the system works.
 * No input spec needed - uses hardcoded test props.
 * 
 * Usage:
 *   npx tsx scripts/test-render.ts [output-path]
 */

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { createRequire } from "module";
import fs from "fs";
import path from "path";

const require = createRequire(import.meta.url);

async function main() {
  const outputPath = process.argv[2] || "test-output.mp4";
  
  console.log("\n🧪 Remotion Test Render");
  console.log("=" .repeat(50));
  console.log(`   Composition: TestTextAnimations`);
  console.log(`   Output: ${outputPath}`);
  
  // Test props
  const inputProps = {
    title: "StreamLine",
    subtitle: "AI-Powered Video Production",
    backgroundColor: "#0f172a",
    primaryColor: "#6366f1",
  };
  
  console.log(`   Title: "${inputProps.title}"`);
  console.log(`   Subtitle: "${inputProps.subtitle}"`);
  
  // Ensure output directory exists
  const outputDir = path.dirname(path.resolve(outputPath));
  if (outputDir && !fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  // Bundle
  console.log("\n📦 Bundling project...");
  const startBundle = Date.now();
  
  const bundled = await bundle({
    entryPoint: require.resolve("../src/index.ts"),
    webpackOverride: (config) => config,
  });
  
  console.log(`   ✓ Bundle complete (${((Date.now() - startBundle) / 1000).toFixed(1)}s)`);
  
  // Select composition
  console.log("\n🎯 Loading composition...");
  const composition = await selectComposition({
    serveUrl: bundled,
    id: "TestTextAnimations",
    inputProps,
  });
  
  console.log(`   ✓ ${composition.id}`);
  console.log(`   ✓ ${composition.durationInFrames} frames @ ${composition.fps}fps`);
  console.log(`   ✓ ${composition.width}x${composition.height}`);
  console.log(`   ✓ Duration: ${(composition.durationInFrames / composition.fps).toFixed(1)}s`);
  
  // Render
  console.log("\n🎥 Rendering video...");
  const startRender = Date.now();
  
  await renderMedia({
    composition,
    serveUrl: bundled,
    codec: "h264",
    outputLocation: outputPath,
    inputProps,
    crf: 18,
    onProgress: ({ progress }) => {
      const percent = Math.round(progress * 100);
      const bar = "█".repeat(Math.floor(percent / 5)) + "░".repeat(20 - Math.floor(percent / 5));
      process.stdout.write(`\r   [${bar}] ${percent}%`);
    },
    chromiumOptions: {
      enableMultiProcessOnLinux: true,
    },
  });
  
  const renderTime = ((Date.now() - startRender) / 1000).toFixed(1);
  const totalTime = ((Date.now() - startBundle) / 1000).toFixed(1);
  
  console.log("\n");
  console.log("=" .repeat(50));
  console.log("✅ TEST RENDER SUCCESSFUL!");
  console.log("=" .repeat(50));
  console.log(`   Output: ${path.resolve(outputPath)}`);
  console.log(`   Render time: ${renderTime}s`);
  console.log(`   Total time: ${totalTime}s`);
  
  // Check file size
  const stats = fs.statSync(outputPath);
  const sizeMB = (stats.size / (1024 * 1024)).toFixed(2);
  console.log(`   File size: ${sizeMB} MB`);
  console.log("\n   🎉 Remotion is working! Your pipeline is ready.\n");
}

main().catch((err) => {
  console.error("\n❌ Test render failed:", err.message || err);
  console.error("\nTroubleshooting:");
  console.error("  1. Run 'npm install' in the remotion directory");
  console.error("  2. Ensure you have Node.js 18+ installed");
  console.error("  3. Check that all dependencies are installed");
  process.exit(1);
});
