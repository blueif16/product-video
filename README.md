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

## Architecture

### Core Principle: Pure LLM Judgment, Zero Parsing

Every decision is made by an LLM with appropriate expertise. No regex, no keyword matching, no hardcoded formulas.

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAPTURE PHASE                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  intake ──────→ Validates project path exists                              │
│      ↓                                                                      │
│  analyze ─────→ Video strategy expert. Decides what to capture.            │
│      ↓                                                                      │
│  capture ─────→ Parallel execution. Screenshots & recordings.              │
│      ↓                                                                      │
│  aggregate ───→ Collects results, status → 'aggregated'                    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         EDITOR PHASE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  planner ─────→ Creative director. Designs video timeline.                 │
│                 Creates "moments" (clip_tasks) with rich notes.            │
│      ↓                                                                      │
│  composer ────→ Motion graphics technician. Builds layer specs.            │
│                 - Image layers (original assets)                           │
│                 - Generated image layers (AI-enhanced)                     │
│                 - Text layers (typography)                                 │
│      ↓                                                                      │
│  assembler ───→ Collects specs → VideoSpec JSON for Remotion               │
│      ↓                                                                      │
│  render ──────→ Remotion CLI produces final MP4                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Layer-Based Architecture (Editor Phase)

Each clip is a **self-contained moment** with multiple layers:

```
┌─────────────────────────────────────────────────────────────┐
│  Clip: "Hero Moment" (0-3s)                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 3 (zIndex: 3): Text "FOCUS"                         │
│    - Appears at 0.5s, typewriter animation                 │
│    - 80px, bold, white, centered                           │
│                                                             │
│  Layer 2 (zIndex: 2): AI-Enhanced Dashboard                │
│    - Glowing version, fades IN (0→1 opacity)               │
│    - Subtle zoom towards task counter                      │
│                                                             │
│  Layer 1 (zIndex: 1): Original Screenshot                  │
│    - Plain dashboard, fades OUT (1→0 opacity)              │
│    - Same zoom animation                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why Layers?

**Before (rigid):**
- Planner creates clip_task (image only)
- Planner creates text_task (text only)
- Two separate things the assembler has to sync

**Now (flexible):**
- Planner creates clip_task with rich creative intent
- Composer interprets and decides what layers to create
- Text, AI enhancements, transitions - all in one spec
- Each moment is self-contained

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
          "type": "image",
          "src": "dashboard.png",
          "zIndex": 1,
          "transform": { "type": "zoom_in", "startScale": 1.0, "endScale": 1.15 },
          "opacity": { "start": 1, "end": 0 }
        },
        {
          "type": "generated_image",
          "src": "dashboard_glowing.png",
          "zIndex": 2,
          "transform": { "type": "zoom_in", "startScale": 1.0, "endScale": 1.15 },
          "opacity": { "start": 0, "end": 1 }
        },
        {
          "type": "text",
          "content": "FOCUS",
          "zIndex": 3,
          "style": { "fontSize": 80, "fontWeight": 800, "color": "#FFFFFF" },
          "animation": { "enter": "typewriter", "exit": "fade" },
          "position": { "preset": "center" },
          "startFrame": 15,
          "durationFrames": 60
        }
      ],
      "enterTransition": { "type": "fade", "durationFrames": 15 }
    }
  ]
}
```

## Project Structure

```
src/
├── config.py                 # API keys, paths, settings
├── main.py                   # Entry point
├── orchestrator/             # Capture phase
│   ├── state.py              # PipelineState
│   ├── intake.py             # Path validation
│   ├── analyzer.py           # Video strategy
│   ├── capturer.py           # Asset capture
│   ├── aggregate.py          # Result collection
│   └── graph.py              # LangGraph wiring
├── editor/                   # Editor phase
│   ├── state.py              # EditorState, Layer types
│   ├── planner.py            # Creative director
│   ├── clip_composer.py      # Layer composition
│   ├── assembler.py          # VideoSpec assembly
│   ├── loader.py             # State loading
│   └── graph.py              # Editor graph
├── tools/
│   ├── bash_tools.py         # Shell commands
│   ├── capture_tools.py      # xcrun simctl wrappers
│   ├── editor_tools.py       # Clip/layer tools
│   └── validation_tool.py    # Multimodal validation
├── renderer/                 # Remotion integration
│   └── render_client.py      # CLI wrapper
└── db/
    ├── migrations/
    │   ├── 001_initial_schema.sql
    │   ├── 002_editor_tables.sql
    │   └── 003_layer_based_clips.sql
    └── supabase_client.py
```

## Database Schema

```sql
-- Video project: THE complete record of a production job
create table video_projects (
    id uuid primary key,
    user_input text not null,
    project_path text,
    app_bundle_id text,
    analysis_summary text,
    status text default 'analyzed',
    editor_status text,  -- 'planning' | 'composing' | 'assembled' | 'rendered'
    created_at timestamptz,
    updated_at timestamptz
);

-- Capture tasks: screenshot/recording jobs
create table capture_tasks (
    id uuid primary key,
    video_project_id uuid references video_projects(id),
    task_description text not null,
    capture_type text not null,  -- 'screenshot' | 'recording'
    asset_path text,
    validation_notes text,
    status text default 'pending'
);

-- Clip tasks: "moments" in the video with rich creative notes
create table clip_tasks (
    id uuid primary key,
    video_project_id uuid references video_projects(id),
    asset_path text,
    start_time_s float not null,
    duration_s float not null,
    composer_notes text not null,  -- Rich creative direction
    clip_spec jsonb,               -- Layer-based composition
    status text default 'pending'
);

-- Generated assets: AI-enhanced images
create table generated_assets (
    id uuid primary key,
    video_project_id uuid references video_projects(id),
    clip_task_id uuid references clip_tasks(id),
    prompt text not null,
    asset_path text,
    asset_url text,
    status text default 'pending'
);

-- Video specs: Final Remotion-ready JSON
create table video_specs (
    id uuid primary key,
    video_project_id uuid references video_projects(id),
    spec jsonb not null,
    version int default 1,
    render_status text default 'pending'
);
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in API keys

# Run migrations in Supabase
# Then:
python -m src.main
```

## Environment Variables

```bash
GEMINI_API_KEY=...           # For LLM (Gemini)
SUPABASE_URL=...             # Your Supabase project URL  
SUPABASE_KEY=...             # Secret key (service_role)
```

## Running the Editor Phase

```python
from editor import run_editor_standalone

# After capture phase completes (status='aggregated')
result = run_editor_standalone("video-project-uuid")

# Access the VideoSpec
print(result["video_spec"])
```

## Status Flow

### Capture Phase
```
analyzed → capturing → aggregated
```

### Editor Phase
```
planning → composing → assembled → rendering → rendered
```

## Design Principles

1. **Layer-Based Composition**
   - Each clip is a stack of composited layers
   - Text is a layer, not a separate track
   - AI enhancements are layers with opacity transitions

2. **Rich Creative Direction**
   - Planner writes full creative intent in `composer_notes`
   - Composer interprets and builds technical layers
   - No lossy field extraction

3. **Every State Change via Tool Call**
   - `create_clip_task()` → writes to DB
   - `submit_clip_spec()` → writes layer spec
   - No parsing LLM output

4. **Flexible Moments**
   - Simple clip: 1 image layer
   - Enhanced clip: original + AI version (crossfade)
   - Rich clip: image + generated + text layers

## Example Creative Flow

**Planner creates:**
```
"Hero moment - make this MAGICAL. Start with plain dashboard, 
crossfade to glowing AI-enhanced version. Add 'NEVER FORGET' 
text that types in at 0.5s. Slow zoom to task counter. 
Premium, confident energy."
```

**Composer produces:**
```json
{
  "layers": [
    { "type": "image", "src": "dashboard.png", "opacity": {"start": 1, "end": 0} },
    { "type": "generated_image", "src": "dashboard_glow.png", "opacity": {"start": 0, "end": 1} },
    { "type": "text", "content": "NEVER FORGET", "animation": {"enter": "typewriter"} }
  ]
}
```

## Troubleshooting

**"No simulator booted"**
```bash
xcrun simctl boot "iPhone 15 Pro"
```

**"No composed specs found"**
- Check `clip_tasks` table for `status='composed'`
- Run composer again if stuck at 'pending'

**"Generated asset not rendering"**
- Check `generated_assets.status` = 'success'
- Verify `asset_url` is populated
