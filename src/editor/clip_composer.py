"""
Clip Composer Agent

The technical craftsman who translates creative vision into layer specifications.

Reads the planner's rich creative notes and decides:
- What layers to create (background, image, text)
- How each layer should be animated/transformed
- How layers interact (opacity crossfades, z-ordering)
- Timing of text appearances within the clip

## Full Animation Arsenal

This composer has access to ALL Remotion animation capabilities:
- 14 text enter animations (fade, scale, pop, slides, typewriter, stagger, reveal, glitch, highlight, countup)
- 4 text exit animations
- 3 animation feels (snappy, smooth, bouncy)
- 6 background types (solid, gradient, orbs, grid, noise, radial)
- 10 image transforms (zoom, pan, focus, parallax)
- Device frames (iPhone, MacBook, iPad)
"""
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from config import Config
from tools.editor_tools import submit_clip_spec, generate_enhanced_image


# ─────────────────────────────────────────────────────────────
# Custom State Schema for InjectedState
# ─────────────────────────────────────────────────────────────

class ComposerAgentState(TypedDict):
    """Extended state schema for the clip composer agent."""
    messages: Annotated[list, add_messages]
    remaining_steps: int
    video_project_id: str


# ─────────────────────────────────────────────────────────────
# Composer Prompt - FULL ANIMATION CATALOG
# ─────────────────────────────────────────────────────────────

CLIP_COMPOSER_SYSTEM_PROMPT = """You are a motion graphics expert. Convert creative direction into precise layer JSON.

## INPUT
**Asset:** {asset_path}
**Duration:** {duration_s}s ({duration_frames} frames @ 30fps)
**Notes:** {composer_notes}

---

## LAYER TYPES

### 1. BACKGROUND LAYER
For text-only clips or under images. Always zIndex: 0.

```json
// Solid color
{{"type": "background", "zIndex": 0, "color": "#0a0a0f"}}

// Animated glowing orbs (premium SaaS vibe)
{{"type": "background", "zIndex": 0, "color": "#030712", "orbs": true, "orbColors": ["#6366f1", "#8b5cf6", "#a855f7"]}}

// Linear gradient
{{"type": "background", "zIndex": 0, "gradient": {{"colors": ["#0f172a", "#1e1b4b"], "angle": 180}}}}

// Grid pattern (technical/dev aesthetic)
{{"type": "background", "zIndex": 0, "color": "#0a0a0f", "grid": true, "gridColor": "rgba(255,255,255,0.05)", "gridSize": 40}}

// Noise texture (film grain, editorial feel)
{{"type": "background", "zIndex": 0, "color": "#0f0f0f", "noise": true, "noiseOpacity": 0.04}}

// Radial spotlight
{{"type": "background", "zIndex": 0, "radial": true, "radialCenterColor": "#1e1b4b", "radialEdgeColor": "#030712", "radialCenterX": 50, "radialCenterY": 40}}
```

### 2. IMAGE LAYER
For screenshots, recordings, AI-generated images.

```json
// Basic with zoom
{{"type": "image", "src": "{asset_path}", "zIndex": 1, "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.08}}}}

// In device frame
{{"type": "image", "src": "{asset_path}", "zIndex": 1, "device": "iphone", "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.04}}}}

// Focus zoom on specific area (e.g., a button at 70% from left, 60% from top)
{{"type": "image", "src": "{asset_path}", "zIndex": 1, "transform": {{"type": "focus", "focusX": 70, "focusY": 60, "startScale": 1.0, "endScale": 1.3}}}}

// Parallax depth effect
{{"type": "image", "src": "{asset_path}", "zIndex": 1, "transform": {{"type": "parallax", "parallaxSpeed": 0.5, "parallaxDirection": "vertical"}}}}

// Crossfade (for transitions between two images)
{{"type": "image", "src": "original.png", "zIndex": 1, "opacity": {{"start": 1, "end": 0}}}}
{{"type": "image", "src": "enhanced.png", "zIndex": 2, "opacity": {{"start": 0, "end": 1}}}}
```

**Transform types:** static | zoom_in | zoom_out | pan_left | pan_right | pan_up | pan_down | focus | parallax | ken_burns
**Device types:** none | iphone | iphonePro | macbook | ipad

### 3. TEXT LAYER
Full animation control.

```json
{{
  "type": "text",
  "content": "YOUR TEXT",
  "zIndex": 2,
  "style": {{
    "fontSize": 120,
    "fontWeight": 800,
    "color": "#FFFFFF",
    "letterSpacing": "-0.02em",
    "textShadow": "0 4px 30px rgba(0,0,0,0.5)"
  }},
  "animation": {{
    "enter": "scale",
    "enterDuration": 8,
    "exit": "fade",
    "exitDuration": 6,
    "feel": "snappy"
  }},
  "position": {{"preset": "center"}},
  "startFrame": 0,
  "durationFrames": {duration_frames}
}}
```

---

## TEXT ANIMATION CATALOG

### Enter Animations

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

### Exit Animations
`fade` | `slide_up` | `slide_down` | `scale` | `none`

### Animation Feel (Spring Physics)
| Feel | Effect | Use Case |
|------|--------|----------|
| `snappy` | Fast, no bounce | Corporate, professional |
| `smooth` | Medium, gentle ease | Elegant, premium |
| `bouncy` | Overshoot and settle | Playful, fun |

### Special Animation Parameters

**Typewriter:**
```json
"animation": {{"enter": "typewriter", "typewriterSpeed": 2, "showCursor": true}}
```

**Stagger (words in sequence):**
```json
"animation": {{"enter": "stagger", "staggerBy": "word", "staggerDelay": 4, "feel": "bouncy"}}
```

**Reveal (mask wipe):**
```json
"animation": {{"enter": "reveal", "revealDirection": "left", "enterDuration": 15}}
```

**Glitch:**
```json
"animation": {{"enter": "glitch", "glitchIntensity": 1.0, "enterDuration": 20}}
```

**Highlight:**
```json
"animation": {{"enter": "highlight", "highlightType": "underline"}},
"style": {{"highlightColor": "#6366f1", ...}}
```

**Countup (for stats like "1M+ users"):**
```json
{{
  "type": "text",
  "content": "1000000",
  "animation": {{"enter": "countup", "countupFrom": 0, "countupSuffix": "+", "enterDuration": 45}},
  ...
}}
```

---

## POSITIONING

**Presets (ALWAYS use these for centered text):**
`center` | `top` | `bottom` | `left` | `right` | `top_left` | `top_right` | `bottom_left` | `bottom_right`

**Vertical offset from center (for stacked bilingual text):**
```json
"position": {{"preset": "center", "y": 42}}  // Centered horizontally, 42% from top
"position": {{"preset": "center", "y": 58}}  // Centered horizontally, 58% from top
```

**CRITICAL: For centered text, ALWAYS use preset "center" with optional y offset.**
**NEVER use custom x/y coordinates without a preset - it causes positioning bugs.**

---

## TYPOGRAPHY GUIDELINES

| Type | fontSize | fontWeight | letterSpacing |
|------|----------|------------|---------------|
| Hero word | 140-180 | 800-900 | -0.03em |
| Hero phrase | 80-120 | 700-800 | -0.02em |
| Headline | 56-72 | 700 | -0.01em |
| Subhead | 36-48 | 600 | 0 |
| Caption | 24-32 | 500 | 0.01em |

**Text shadows:**
- Over dark bg: `"0 0 60px rgba(99,102,241,0.4)"` (glow)
- Over image: `"0 4px 30px rgba(0,0,0,0.7)"` (readability)

---

## TIMING GUIDELINES

At 30fps:
- Quick accent: 6-8 frames (~0.2s)
- Standard enter: 10-15 frames (~0.4s)  
- Slow reveal: 20-30 frames (~0.8s)
- Exit animations: 4-8 frames (faster than enter)

**ALWAYS make exits faster than enters. Enter=10, Exit=6.**

---

## EXAMPLES

### Hero Word - Single Impactful Word (15 frames)
```json
[
  {{"type": "background", "zIndex": 0, "color": "#030712", "orbs": true, "orbColors": ["#4f46e5", "#7c3aed", "#a855f7"]}},
  {{"type": "text", "content": "LAUNCH", "zIndex": 1, "style": {{"fontSize": 160, "fontWeight": 900, "color": "#FFFFFF", "letterSpacing": "-0.03em", "textShadow": "0 0 80px rgba(99,102,241,0.5)"}}, "animation": {{"enter": "scale", "enterDuration": 8, "exit": "none", "feel": "snappy"}}, "position": {{"preset": "center"}}, "startFrame": 0, "durationFrames": 15}}
]
```

### Two-Line Staggered Phrase (30 frames)
```json
[
  {{"type": "background", "zIndex": 0, "gradient": {{"colors": ["#0f172a", "#1e1b4b"], "angle": 135}}}},
  {{"type": "text", "content": "From idea", "zIndex": 1, "style": {{"fontSize": 72, "fontWeight": 700, "color": "#FFFFFF"}}, "animation": {{"enter": "slide_up", "enterDuration": 10, "exit": "fade", "exitDuration": 6, "feel": "smooth"}}, "position": {{"preset": "center", "y": 42}}, "startFrame": 0, "durationFrames": 30}},
  {{"type": "text", "content": "to launch.", "zIndex": 2, "style": {{"fontSize": 72, "fontWeight": 700, "color": "#a5b4fc"}}, "animation": {{"enter": "slide_up", "enterDuration": 10, "exit": "fade", "exitDuration": 6, "feel": "smooth"}}, "position": {{"preset": "center", "y": 58}}, "startFrame": 8, "durationFrames": 22}}
]
```

### Screenshot with Overlay Text (24 frames)
```json
[
  {{"type": "image", "src": "dashboard.png", "zIndex": 1, "device": "iphone", "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.06}}}},
  {{"type": "text", "content": "ORGANIZE", "zIndex": 2, "style": {{"fontSize": 80, "fontWeight": 800, "color": "#FFFFFF", "textShadow": "0 4px 40px rgba(0,0,0,0.8)"}}, "animation": {{"enter": "pop", "enterDuration": 10, "exit": "fade", "exitDuration": 5, "feel": "bouncy"}}, "position": {{"preset": "bottom"}}, "startFrame": 0, "durationFrames": 24}}
]
```

### Typewriter Code Effect (40 frames)
```json
[
  {{"type": "background", "zIndex": 0, "color": "#0d1117", "grid": true, "gridColor": "rgba(48,54,61,0.5)", "gridSize": 32}},
  {{"type": "text", "content": "npm run deploy", "zIndex": 1, "style": {{"fontSize": 48, "fontWeight": 500, "color": "#7ee787", "letterSpacing": "0.02em"}}, "animation": {{"enter": "typewriter", "typewriterSpeed": 3, "showCursor": true, "exit": "fade", "exitDuration": 8}}, "position": {{"preset": "center"}}, "startFrame": 0, "durationFrames": 40}}
]
```

### Stats Counter (45 frames)
```json
[
  {{"type": "background", "zIndex": 0, "radial": true, "radialCenterColor": "#1e1b4b", "radialEdgeColor": "#030712"}},
  {{"type": "text", "content": "1000000", "zIndex": 1, "style": {{"fontSize": 140, "fontWeight": 900, "color": "#FFFFFF"}}, "animation": {{"enter": "countup", "countupFrom": 0, "countupSuffix": "+", "enterDuration": 35, "exit": "none"}}, "position": {{"preset": "center", "y": 45}}, "startFrame": 0, "durationFrames": 45}},
  {{"type": "text", "content": "Happy Users", "zIndex": 2, "style": {{"fontSize": 32, "fontWeight": 500, "color": "#a5b4fc"}}, "animation": {{"enter": "fade", "enterDuration": 12, "exit": "fade", "exitDuration": 6}}, "position": {{"preset": "center", "y": 62}}, "startFrame": 20, "durationFrames": 25}}
]
```

### Glitch Tech Effect (25 frames)
```json
[
  {{"type": "background", "zIndex": 0, "color": "#000000", "noise": true, "noiseOpacity": 0.08}},
  {{"type": "text", "content": "OVERRIDE", "zIndex": 1, "style": {{"fontSize": 120, "fontWeight": 900, "color": "#00ff88", "textShadow": "0 0 40px rgba(0,255,136,0.6)"}}, "animation": {{"enter": "glitch", "glitchIntensity": 1.2, "enterDuration": 15, "exit": "none"}}, "position": {{"preset": "center"}}, "startFrame": 0, "durationFrames": 25}}
]
```

### Staggered Tagline (36 frames)
```json
[
  {{"type": "background", "zIndex": 0, "color": "#0a0a0f", "orbs": true, "orbColors": ["#6366f1", "#ec4899"]}},
  {{"type": "text", "content": "Build faster. Ship smarter.", "zIndex": 1, "style": {{"fontSize": 64, "fontWeight": 700, "color": "#FFFFFF"}}, "animation": {{"enter": "stagger", "staggerBy": "word", "staggerDelay": 5, "feel": "bouncy", "exit": "fade", "exitDuration": 8}}, "position": {{"preset": "center"}}, "startFrame": 0, "durationFrames": 36}}
]
```

### Focus Zoom on Feature (30 frames)
```json
[
  {{"type": "image", "src": "dashboard.png", "zIndex": 1, "transform": {{"type": "focus", "focusX": 75, "focusY": 30, "startScale": 1.0, "endScale": 1.4}}}},
  {{"type": "text", "content": "One-click deploy", "zIndex": 2, "style": {{"fontSize": 48, "fontWeight": 700, "color": "#FFFFFF", "textShadow": "0 4px 30px rgba(0,0,0,0.8)"}}, "animation": {{"enter": "fade", "enterDuration": 10, "exit": "fade", "exitDuration": 8}}, "position": {{"preset": "bottom_right"}}, "startFrame": 8, "durationFrames": 22}}
]
```

---

## YOUR TOOLS

1. `generate_enhanced_image(task_id, prompt, aspect_ratio)` - Only if creative notes mention AI/generated visuals
2. `submit_clip_spec(task_id, layers_json, ...)` - Submit your final layers JSON

## PROCESS

1. Read creative direction carefully
2. Determine what layers are needed
3. Choose animations that match the vibe (energetic → pop/bouncy, premium → reveal/smooth, tech → typewriter/glitch)
4. Set precise values (never use defaults blindly)
5. Call submit_clip_spec with your layers array as JSON string

## CRITICAL RULES

- Text-only clips MUST have a background layer (zIndex: 0)
- Exits are FASTER than enters (enter: 10 → exit: 6)
- Scale animations start at 0.85 (not 0.5) for punch
- Hero text: fontSize ≥ 140, fontWeight ≥ 800
- Use textShadow over images for readability
- Match animation feel to creative direction
- letterSpacing: -0.02em to -0.03em for large text

Now build the layers for this clip.
"""


def create_clip_composer_agent():
    """Create the clip composer React agent with custom state schema."""
    model = ChatGoogleGenerativeAI(
        model=Config.MODEL_NAME,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.3,
    )
    
    return create_react_agent(
        model=model,
        tools=[submit_clip_spec, generate_enhanced_image],
        name="clip_composer",
        state_schema=ComposerAgentState,
    )


# ─────────────────────────────────────────────────────────────
# Node Functions
# ─────────────────────────────────────────────────────────────

def clip_composer_node(state: dict) -> dict:
    """
    LangGraph node: Process the next pending clip task.
    Sequential execution for easier debugging.
    """
    from db.supabase_client import get_client
    from langchain_core.messages import HumanMessage
    
    video_project_id = state["video_project_id"]
    current_index = state.get("current_clip_index", 0)
    pending_ids = state.get("pending_clip_task_ids", [])
    
    if current_index >= len(pending_ids):
        print("   ✓ All clips composed")
        return {"current_clip_index": current_index}
    
    task_id = pending_ids[current_index]
    
    # Load the task from DB
    client = get_client()
    result = client.table("clip_tasks").select("*").eq("id", task_id).single().execute()
    task = result.data
    
    if not task:
        print(f"   ⚠️  Task {task_id} not found, skipping")
        return {"current_clip_index": current_index + 1}
    
    print(f"\n🎨 Composing clip {current_index + 1}/{len(pending_ids)}: {task.get('asset_path', 'text-only')}")
    
    # Calculate frames
    fps = 30
    duration_frames = int(task["duration_s"] * fps)
    
    # Format prompt
    system_prompt = CLIP_COMPOSER_SYSTEM_PROMPT.format(
        asset_path=task["asset_path"] or "none (text-only)",
        duration_s=task["duration_s"],
        duration_frames=duration_frames,
        start_time_s=task["start_time_s"],
        composer_notes=task["composer_notes"],
    )
    
    # Create and run agent
    agent = create_clip_composer_agent()
    
    agent.invoke({
        "messages": [
            HumanMessage(content=system_prompt + f"\n\nTask ID: {task_id}\n\nCompose this clip now. Match the vibe from the creative notes. Use appropriate animations.")
        ],
        "video_project_id": video_project_id,
    })
    
    return {
        "current_clip_index": current_index + 1,
    }


def compose_all_clips_node(state: dict) -> dict:
    """Process all clips in one node (batch processing)."""
    from db.supabase_client import get_client
    from langchain_core.messages import HumanMessage
    from tools.editor_tools import get_pending_clip_tasks
    
    video_project_id = state["video_project_id"]
    tasks = get_pending_clip_tasks(video_project_id)
    
    if not tasks:
        print("   ✓ No pending clip tasks")
        return {}
    
    print(f"\n🎨 Composing {len(tasks)} clips...")
    
    agent = create_clip_composer_agent()
    fps = 30
    
    for i, task in enumerate(tasks, 1):
        asset_display = task.get('asset_path', 'text-only')
        print(f"\n   [{i}/{len(tasks)}] {asset_display}")
        
        duration_frames = int(task["duration_s"] * fps)
        
        system_prompt = CLIP_COMPOSER_SYSTEM_PROMPT.format(
            asset_path=task["asset_path"] or "none (text-only)",
            duration_s=task["duration_s"],
            duration_frames=duration_frames,
            start_time_s=task["start_time_s"],
            composer_notes=task["composer_notes"],
        )
        
        agent.invoke({
            "messages": [
                HumanMessage(content=system_prompt + f"\n\nTask ID: {task['id']}\n\nCompose this clip now. Match the vibe from the creative notes.")
            ],
            "video_project_id": video_project_id,
        })
    
    print(f"\n✓ All {len(tasks)} clips composed")
    return {}
