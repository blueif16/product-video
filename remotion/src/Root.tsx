import { Composition } from "remotion";
import { TestTextAnimations, testTextAnimationsSchema } from "./compositions/TestTextAnimations";
import { ProductVideo, productVideoSchema } from "./compositions/ProductVideo";
import { Thumbnail, thumbnailSchema } from "./compositions/Thumbnail";
import { AnimationShowcase, animationShowcaseSchema } from "./compositions/AnimationShowcase";

// Scene components for standalone testing
import { HeroScene, heroSceneSchema } from "./scenes/HeroScene";
import { FeatureScene, featureSceneSchema } from "./scenes/FeatureScene";
import { ScreenshotScene, screenshotSceneSchema } from "./scenes/ScreenshotScene";
import { CTAScene, ctaSceneSchema } from "./scenes/CTAScene";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* ─────────────────────────────────────────────────────────────
          MAIN COMPOSITIONS
          ───────────────────────────────────────────────────────────── */}
      
      {/* Main production composition */}
      <Composition
        id="ProductVideo"
        component={ProductVideo}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
        schema={productVideoSchema}
        defaultProps={{
          meta: {
            title: "Product Demo",
            durationFrames: 900,
            fps: 30,
            resolution: { width: 1920, height: 1080 },
          },
          clips: [],
        }}
        calculateMetadata={async ({ props }) => {
          return {
            durationInFrames: props.meta?.durationFrames || 900,
          };
        }}
      />

      {/* Thumbnail/still image composition */}
      <Composition
        id="Thumbnail"
        component={Thumbnail}
        durationInFrames={1}
        fps={30}
        width={1920}
        height={1080}
        schema={thumbnailSchema}
        defaultProps={{
          title: "Your Product",
          subtitle: "The tagline goes here",
          showDevice: false,
          device: "iphone",
          layout: "centered",
        }}
      />

      {/* ─────────────────────────────────────────────────────────────
          ANIMATION SHOWCASE (Visual test of ALL animations)
          ───────────────────────────────────────────────────────────── */}

      <Composition
        id="AnimationShowcase"
        component={AnimationShowcase}
        durationInFrames={75 * 20}  // 20 clips × 75 frames each
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{}}
      />

      {/* ─────────────────────────────────────────────────────────────
          TEST COMPOSITIONS
          ───────────────────────────────────────────────────────────── */}

      {/* Test composition - text animations */}
      <Composition
        id="TestTextAnimations"
        component={TestTextAnimations}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        schema={testTextAnimationsSchema}
        defaultProps={{
          title: "StreamLine",
          subtitle: "AI-Powered Video Production",
          backgroundColor: "#0f172a",
          primaryColor: "#6366f1",
        }}
      />

      {/* ─────────────────────────────────────────────────────────────
          SCENE PREVIEWS (for testing individual scenes)
          ───────────────────────────────────────────────────────────── */}

      {/* Hero Scene */}
      <Composition
        id="Scene-Hero"
        component={HeroScene}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
        schema={heroSceneSchema}
        defaultProps={{
          title: "FocusFlow",
          subtitle: "Your tasks, organized beautifully",
          tagline: "INTRODUCING",
          showOrbs: true,
        }}
      />

      {/* Feature Scene */}
      <Composition
        id="Scene-Feature"
        component={FeatureScene}
        durationInFrames={120}
        fps={30}
        width={1920}
        height={1080}
        schema={featureSceneSchema}
        defaultProps={{
          title: "Smart Task Prioritization",
          description: "AI automatically organizes your tasks based on urgency and importance",
          featureNumber: 1,
          totalFeatures: 3,
          layout: "center",
        }}
      />

      {/* Screenshot Scene */}
      <Composition
        id="Scene-Screenshot"
        component={ScreenshotScene}
        durationInFrames={75}
        fps={30}
        width={1920}
        height={1080}
        schema={screenshotSceneSchema}
        defaultProps={{
          screenshot: "https://via.placeholder.com/1170x2532/1e293b/ffffff?text=App+Screenshot",
          caption: "Beautiful Dashboard",
          subcaption: "Everything you need at a glance",
          device: "iphone",
          kenBurns: "zoom-in",
          floating: true,
        }}
      />

      {/* CTA Scene */}
      <Composition
        id="Scene-CTA"
        component={CTAScene}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
        schema={ctaSceneSchema}
        defaultProps={{
          headline: "Ready to Focus?",
          subheadline: "Join thousands of productive users",
          ctaText: "Try Free Today",
          ctaUrl: "focusflow.app",
          showArrow: true,
        }}
      />
    </>
  );
};
