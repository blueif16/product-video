import { Config } from "@remotion/cli/config";

// Output settings
Config.setVideoImageFormat("png");
Config.setOverwriteOutput(true);

// Performance optimization
Config.setConcurrency(4);
Config.setChromiumOpenGlRenderer("angle");

// Quality defaults
Config.setQuality(80);
