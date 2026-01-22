# Product Video Pipeline

AI-powered product video generation for Product Hunt launches and SaaS marketing.

**You describe your app. It creates the video.**

## What This Does

```
"My app FocusFlow is a minimalist task manager with smooth animations. 
 I want a 30-second energetic promo for Product Hunt. 
 Project is at ~/Code/FocusFlow/FocusFlow.xcodeproj"
         ↓
   [Analyzes code, captures screens]
         ↓
   [Creates layered video spec]
         ↓
   [Renders with Remotion]
         ↓
   Final MP4 ready for Product Hunt
```

---

## Animation Catalog

The system has a comprehensive animation library with **14 text animations**, **6 background types**, **10 image transforms**, and **3 animation feels**.

### Text Animations

| Animation | Effect | Best For |
|-----------|--------|----------|
| `fade` | Simple opacity 0→1 | Subtle, elegant |
| `scale` | Scale 0.85→1 with fade | Punchy, confident |
| `pop` | Scale with bounce overshoot | Playful, energetic |
| `slide_up` | Slide from bottom | Reveals, lists |
| `slide_down` | Slide from top | Headlines |
| `slide_left` | Slide from right | Sequential info |
| `slide_right` | Slide from left | Sequential info |
| `typewriter` | Characters appear 1 by 1 | Code, terminals |
| `stagger` | Words animate in sequence | Phrases, taglines |
| `reveal` | Mask wipe reveal | Premium, cinematic |
| `glitch` | Distortion then settle | Tech, edgy |
| `highlight` | Animated underline/bg | Emphasis |
| `countup` | Number 0 → target | Stats, metrics |
| `none` | Instant appear | Hard cuts |

### Animation Feel (Spring Physics)

| Feel | Effect | Use Case |
|------|--------|----------|
| `snappy` | Fast, no bounce | Corporate, professional |
| `smooth` | Medium, gentle ease | Elegant, premium |
| `bouncy` | Overshoot and settle | Playful, fun |

### Background Types

| Type | Effect |
|------|--------|
| `color` | Solid hex color |
| `gradient` | Linear gradient with angle |
| `orbs` | Animated glowing spheres (SaaS vibe) |
| `grid` | Technical grid pattern |
| `noise` | Film grain texture |
| `radial` | Centered radial gradient (spotlight) |

### Image Transforms

| Transform | Effect |
|-----------|--------|
| `zoom_in` | Slow zoom towards center |
| `zoom_out` | Slow zoom away |
| `pan_left/right/up/down` | Directional drift |
| `focus` | Zoom towards specific point |
| `parallax` | Depth-based scrolling |
| `ken_burns` | Classic documentary zoom |
| `static` | No movement |

### Test Animations

Run the Remotion preview to see all animations:

```bash
cd remotion
npm run dev
# Open http://localhost:3000 and select "AnimationShowcase"
```

---

## Architecture

### Core Principle: Pure LLM Judgment, Zero Parsing

Every decision is made by an LLM with appropriate expertise. No regex, no keyword matching, no hardcoded formulas.

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAPTURE PHASE                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  intake ──────→ Validates project path exists                              │
│      ↓                                                                      │
│  analyze ─────→ Video strategy expert. Decides what to capture.            │
│      ↓                                                                      │
│  capture ─────→ Parallel execution. Screenshots & recordings.              │
│      ↓                                                                      │
│  aggregate ───→ Collects results, status → 'aggregated'                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                         EDITOR PHASE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  planner ─────→ Creative director. Designs video timeline.                 │
│      ↓                                                                      │
│  composer ────→ Motion graphics expert. Builds layer specs.                │
│      ↓                                                                      │
│  assembler ───→ Collects specs → VideoSpec JSON for Remotion               │
│      ↓                                                                      │
│  render ──────→ Remotion CLI produces final MP4                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer-Based Architecture

Each clip is a **self-contained moment** with multiple layers:

```
┌─────────────────────────────────────────────────────────────┐
│  Clip: "Hero Moment" (0-3s)                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 3 (zIndex: 3): Text "FOCUS"                         │
│    - animation: "typewriter"                               │
│    - feel: "snappy"                                        │
│                                                             │
│  Layer 2 (zIndex: 2): AI-Generated Image                   │
│    - opacity: 0 → 1 (crossfade in)                         │
│                                                             │
│  Layer 1 (zIndex: 1): Original Screenshot                  │
│    - opacity: 1 → 0 (crossfade out)                        │
│    - transform: zoom_in                                    │
│                                                             │
│  Layer 0 (zIndex: 0): Background                           │
│    - orbs: true, orbColors: ["#6366f1", "#8b5cf6"]         │
└─────────────────────────────────────────────────────────────┘
```

### Example VideoSpec

```json
{
  "meta": {
    "title": "FocusFlow Promo",
    "durationFrames": 900,
    "fps": 30,
    "resolution": { "width": 1920, "height": 1080 }
  },
  "clips": [
    {
      "id": "clip-001",
      "startFrame": 0,
      "durationFrames": 90,
      "layers": [
        {
          "type": "background",
          "zIndex": 0,
          "color": "#030712",
          "orbs": true,
          "orbColors": ["#6366f1", "#8b5cf6"]
        },
        {
          "type": "image",
          "src": "dashboard.png",
          "zIndex": 1,
          "transform": { "type": "zoom_in", "startScale": 1.0, "endScale": 1.08 },
          "device": "iphone"
        },
        {
          "type": "text",
          "content": "ORGANIZE",
          "zIndex": 2,
          "style": { "fontSize": 120, "fontWeight": 800, "color": "#FFFFFF" },
          "animation": { "enter": "pop", "exit": "fade", "feel": "bouncy" },
          "position": { "preset": "bottom" },
          "startFrame": 0,
          "durationFrames": 90
        }
      ]
    }
  ]
}
```

---

## Project Structure

```
src/
├── config.py                 # API keys, paths, settings
├── main.py                   # Entry point
├── orchestrator/             # Capture phase
│   ├── state.py              
│   ├── intake.py             
│   ├── analyzer.py           
│   ├── capturer.py           
│   ├── aggregate.py          
│   └── graph.py              
├── editor/                   # Editor phase
│   ├── state.py              # Full animation type definitions
│   ├── planner.py            
│   ├── clip_composer.py      # 14 animation types in prompt
│   ├── assembler.py          
│   ├── loader.py             
│   └── graph.py              
├── tools/
│   ├── editor_tools.py       # Clip/layer tools
│   └── ...
├── renderer/                 
│   └── render_client.py      
└── db/
    └── supabase_client.py

remotion/
├── src/
│   ├── components/
│   │   ├── AnimatedText.tsx  # 7 text animation components
│   │   ├── SlideIn.tsx       # 4 directions + feel param
│   │   ├── ScaleIn.tsx       # Scale + PopIn + ZoomIn
│   │   ├── FadeIn.tsx        # Fade + FadeInOut
│   │   ├── Background.tsx    # 6 background types
│   │   ├── KenBurns.tsx      # 10 image transforms
│   │   └── index.ts          
│   ├── compositions/
│   │   ├── ProductVideo.tsx  # Main renderer
│   │   └── AnimationShowcase.tsx  # Visual test
│   └── Root.tsx
```

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in API keys

# Start Remotion preview
cd remotion && npm install && npm run dev

# Run the pipeline
python -m src.main
```

## Environment Variables

```bash
GEMINI_API_KEY=...           # For LLM (Gemini)
SUPABASE_URL=...             # Your Supabase project URL  
SUPABASE_KEY=...             # Secret key (service_role)
```

---

## Design Principles

1. **Full Animation Arsenal**
   - 14 text animations, 6 backgrounds, 10 transforms
   - Spring physics control via `feel` parameter
   - All exposed to the Composer agent

2. **Unified Image Type**
   - All images use `"type": "image"` with a `src` path
   - No distinction between captured and generated

3. **Layer-Based Composition**
   - Each clip is a stack of composited layers
   - Text, images, backgrounds can all coexist
   - Z-index controls stacking order

4. **Every State Change via Tool Call**
   - `create_clip_task()` → writes to DB
   - `submit_clip_spec()` → writes layer spec
   - No parsing LLM output

---

## Troubleshooting

**"No simulator booted"**
```bash
xcrun simctl boot "iPhone 15 Pro"
```

**Animation not working?**
```bash
cd remotion && npm run dev
# Select "AnimationShowcase" to verify all animations work
```

**Composer not using new animations?**
- Check `clip_composer.py` has the updated prompt with all 14 animations
- The `state.py` must have the animation types in `TextAnimationSpec`
