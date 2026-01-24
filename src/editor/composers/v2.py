"""
Clip Composer Agent V2

Builds layer specs from creative direction.
Reads composer_notes (which contain full style decisions from planner).
"""
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from config import Config
from tools.editor_tools import submit_clip_spec, generate_enhanced_image


class ComposerAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: int
    video_project_id: str
    clip_id: str


CLIP_COMPOSER_SYSTEM_PROMPT = """You are a motion graphics technician. Build layer specs from creative direction.

## YOUR ASSIGNMENT

**Clip ID:** {clip_id}
**Asset:** {asset_path}
**Duration:** {duration_s}s ({duration_frames} frames @ 30fps)

**Creative Direction (from planner - follow this closely):**
{composer_notes}

---

## LAYER TYPES

### Background
```json
// Solid (for clean, elegant looks)
{{"type": "background", "zIndex": 0, "color": "#FAF5EF"}}

// With animated orbs (for energetic, modern looks)
{{"type": "background", "zIndex": 0, "color": "#0a0a0f", "orbs": true, "orbColors": ["#6366f1", "#ec4899", "#8b5cf6"]}}

// Gradient
{{"type": "background", "zIndex": 0, "gradient": {{"colors": ["#0a0a0f", "#1e1b4b"], "angle": 180}}}}

// Grid pattern (for technical looks)
{{"type": "background", "zIndex": 0, "color": "#0d1117", "grid": true, "gridColor": "rgba(255,255,255,0.05)"}}
```

### Image
```json
// Basic with motion
{{"type": "image", "src": "path.png", "zIndex": 1, "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.08}}}}

// In device frame
{{"type": "image", "src": "path.png", "zIndex": 1, "device": "iphone", "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.04}}}}

// Focus on specific area
{{"type": "image", "src": "path.png", "zIndex": 1, "transform": {{"type": "focus", "focusX": 70, "focusY": 30, "startScale": 1.0, "endScale": 1.3}}}}
```

Transform types: zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down, focus, static

### Text
```json
{{
  "type": "text",
  "content": "YOUR TEXT",
  "zIndex": 2,
  "style": {{
    "fontSize": 160,
    "fontWeight": 800,
    "color": "#1a1a1a",
    "letterSpacing": "-0.02em",
    "textShadow": "0 4px 30px rgba(0,0,0,0.3)"  // optional
  }},
  "animation": {{
    "enter": "scale",
    "enterDuration": 10,
    "exit": "fade",
    "exitDuration": 6,
    "feel": "smooth"
  }},
  "position": {{"preset": "center"}},
  "startFrame": 0,
  "durationFrames": 60
}}
```

**Position presets:** center, top, bottom, left, right, top_left, top_right, bottom_left, bottom_right

**Custom position:** `{{"x": 50, "y": 20}}` (percentage from top-left)

**Enter animations:** fade, scale, pop, slide_up, slide_down, slide_left, slide_right, typewriter, stagger, reveal, glitch, highlight, countup, none

**Exit animations:** fade, slide_up, slide_down, scale, none

**Feel:** snappy (fast/punchy), smooth (elegant), bouncy (playful)

---

## KEY RULES

1. **Read the creative direction carefully** - it contains the planner's style decisions (colors, bg type, animation feel)

2. **Text-only clips need a background layer** (zIndex: 0)
   - Use the background type specified in creative direction (solid vs orbs vs gradient)

3. **Device frames (iphone/ipad):** The device sits in CENTER of screen. Put text at:
   - `"preset": "top"` (above device)
   - `{{"x": 50, "y": 15}}` (explicit top area)
   - `{{"x": 50, "y": 88}}` (below device)
   
   Avoid `"preset": "center"` or `"bottom"` with device frames - text will overlap the phone.

4. **Duration math:** 
   - 30fps, so 1 second = 30 frames
   - Enter animation typically 8-12 frames
   - Exit animation typically 5-8 frames

5. **Layer order:** background (0) → image (1) → text (2+)

6. **Use colors from creative direction** - the planner has already decided what works for this app

---

## EXAMPLES

**Light theme (solid background):**
```json
[
  {{"type": "background", "zIndex": 0, "color": "#FAF5EF"}},
  {{"type": "text", "content": "SIMPLE", "zIndex": 1, "style": {{"fontSize": 160, "fontWeight": 800, "color": "#1a1a1a"}}, "animation": {{"enter": "fade", "enterDuration": 15, "exit": "fade", "exitDuration": 10, "feel": "smooth"}}, "position": {{"preset": "center"}}, "startFrame": 0, "durationFrames": 30}}
]
```

**Dark theme (with orbs):**
```json
[
  {{"type": "background", "zIndex": 0, "color": "#0a0a0f", "orbs": true, "orbColors": ["#6366f1", "#ec4899", "#8b5cf6"]}},
  {{"type": "text", "content": "LAUNCH", "zIndex": 1, "style": {{"fontSize": 160, "fontWeight": 800, "color": "#ffffff"}}, "animation": {{"enter": "scale", "enterDuration": 8, "exit": "none", "feel": "snappy"}}, "position": {{"preset": "center"}}, "startFrame": 0, "durationFrames": 18}}
]
```

**Screenshot with device + text at top:**
```json
[
  {{"type": "background", "zIndex": 0, "color": "#F5F2ED"}},
  {{"type": "image", "src": "dashboard.png", "zIndex": 1, "device": "iphone", "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.06}}}},
  {{"type": "text", "content": "ORGANIZE", "zIndex": 2, "style": {{"fontSize": 80, "fontWeight": 800, "color": "#1a1a1a", "textShadow": "0 4px 30px rgba(0,0,0,0.2)"}}, "animation": {{"enter": "slide_up", "enterDuration": 10, "exit": "fade", "exitDuration": 6, "feel": "smooth"}}, "position": {{"preset": "top"}}, "startFrame": 9, "durationFrames": 66}}
]
```

---

## TOOLS

1. `submit_clip_spec(task_id, layers_json, ...)` - Submit your layers
2. `generate_enhanced_image(task_id, prompt, aspect_ratio)` - Only if creative notes request AI enhancement

---

Read the creative direction. Build layers that match the planner's vision.
"""


def create_clip_composer_agent():
    """Create the clip composer React agent."""
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


def compose_single_clip_node(state: dict) -> dict:
    """Compose ONE clip. For parallel execution via Send."""
    from db.supabase_client import get_client
    from langchain_core.messages import HumanMessage
    from tools.storage import resolve_asset_src
    
    clip_id = state["clip_id"]
    video_project_id = state["video_project_id"]
    
    client = get_client()
    result = client.table("clip_tasks").select("*").eq("id", clip_id).single().execute()
    task = result.data
    
    if not task:
        print(f"   ⚠️  Clip {clip_id} not found")
        return {}
    
    # Cloud-first: prefer asset_url over asset_path
    asset_src = resolve_asset_src(task.get("asset_url"), task.get("asset_path"))
    print(f"\n   [{clip_id[:8]}] {asset_src}")
    
    fps = 30
    duration_frames = int(task["duration_s"] * fps)
    
    system_prompt = CLIP_COMPOSER_SYSTEM_PROMPT.format(
        clip_id=clip_id,
        asset_path=asset_src,  # Uses resolved URL or path
        duration_s=task["duration_s"],
        duration_frames=duration_frames,
        composer_notes=task["composer_notes"],
    )
    
    agent = create_clip_composer_agent()
    
    agent.invoke({
        "messages": [HumanMessage(content=system_prompt + f"\n\nBuild layers for clip {clip_id}.")],
        "video_project_id": video_project_id,
        "clip_id": clip_id,
    })
    
    return {}


def compose_all_clips_node(state: dict) -> dict:
    """Compose all clips sequentially."""
    from tools.editor_tools import get_pending_clip_tasks
    
    video_project_id = state["video_project_id"]
    tasks = get_pending_clip_tasks(video_project_id)
    
    if not tasks:
        print("   ✓ No pending clip tasks")
        return {}
    
    print(f"\n🎨 Composing {len(tasks)} clips...")
    
    for i, task in enumerate(tasks, 1):
        asset_display = task.get('asset_path') or 'text-only'
        if len(asset_display) > 50:
            asset_display = "..." + asset_display[-47:]
        print(f"\n   [{i}/{len(tasks)}] {asset_display}")
        
        compose_single_clip_node({
            "clip_id": task["id"],
            "video_project_id": video_project_id,
        })
    
    print(f"\n✓ All {len(tasks)} clips composed")
    return {}
