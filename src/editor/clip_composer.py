"""
Clip Composer Agent

The technical craftsman who translates creative vision into layer specifications.

Reads the planner's rich creative notes and decides:
- What layers to create (image, generated_image, text)
- How each layer should be animated/transformed
- How layers interact (opacity crossfades, z-ordering)
- Timing of text appearances within the clip

This agent has access to:
- submit_clip_spec: Submit the final layer-based specification
- generate_enhanced_image: Request AI image generation (when needed)
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from config import Config
from tools.editor_tools import submit_clip_spec, generate_enhanced_image


# ─────────────────────────────────────────────────────────────
# Composer Prompt
# ─────────────────────────────────────────────────────────────

CLIP_COMPOSER_SYSTEM_PROMPT = """You are a motion graphics compositor implementing a creative director's vision.

## Your Task

Read the creative direction carefully and build a LAYERED composition.
The planner told you what they WANT. Your job is to figure out HOW.

## Task Details

**Asset:** {asset_path}
**Duration:** {duration_s} seconds ({duration_frames} frames at 30fps)
**Start Time:** {start_time_s}s

**Creative Direction:**
{composer_notes}

## Understanding Layers

A clip is a STACK of layers composited together:
- Higher zIndex = on top
- Each layer can have its own transform, opacity, timing
- Layers can fade in/out independently

Example: "Magical hero moment with text"
```
Layer 1 (zIndex: 1): Original screenshot - fades OUT from 1.0 to 0.0
Layer 2 (zIndex: 2): AI-enhanced version - fades IN from 0.0 to 1.0
Layer 3 (zIndex: 3): "FOCUS" text - appears at frame 15, scales in
```

## Layer Types

### Image Layer (original asset)
Use for the screenshot/recording itself.

```json
{{
  "type": "image",
  "src": "{asset_path}",
  "zIndex": 1,
  "transform": {{
    "type": "zoom_in",
    "startScale": 1.0,
    "endScale": 1.2,
    "startX": 0, "endX": 5,
    "startY": 0, "endY": -3,
    "easing": "ease_out"
  }},
  "opacity": {{"start": 1, "end": 1}},
  "deviceFrame": {{"type": "iphone_15", "shadow": true}}
}}
```

### Generated Image Layer (AI-enhanced)
Use when the creative notes mention "enhanced", "glow", "magical", "artistic".
First call generate_enhanced_image(), then include the layer.

```json
{{
  "type": "generated_image",
  "generatedAssetId": "uuid-from-generate-tool",
  "src": "",
  "zIndex": 2,
  "transform": {{...}},
  "opacity": {{"start": 0, "end": 1}}
}}
```

### Text Layer
For any text overlays mentioned in the creative notes.

```json
{{
  "type": "text",
  "content": "FOCUS",
  "zIndex": 3,
  "style": {{
    "fontSize": 72,
    "fontWeight": 800,
    "color": "#FFFFFF",
    "fontFamily": "Inter"
  }},
  "animation": {{
    "enter": "scale",
    "exit": "fade",
    "enterDurationFrames": 12,
    "exitDurationFrames": 10
  }},
  "position": {{"preset": "center"}},
  "startFrame": 15,
  "durationFrames": 45
}}
```

## Transform Reference

| Type | Effect | Use When |
|------|--------|----------|
| static | No movement | Brief holds, clean presentation |
| ken_burns | Slow zoom + pan | Documentary feel, breathing room |
| zoom_in | Zoom towards focal point | Focus attention, building energy |
| zoom_out | Zoom away | Reveal context, release tension |
| pan | Horizontal/vertical movement | Scanning, following action |

### Scale Guidelines
- 1.0 = 100% (no zoom)
- 1.05-1.1 = Subtle (calm, professional)
- 1.1-1.2 = Noticeable (moderate energy)
- 1.2-1.4 = Dramatic (high energy)

### Easing
- spring: Bouncy, organic (overshoots then settles)
- ease_out: Smooth deceleration (confident)
- ease_in_out: Smooth both ends (elegant)
- linear: Mechanical (rarely used)

## Text Animation Reference

**Enter animations:**
- fade: Elegant opacity change
- slide_up/down/left/right: Direction-based slide
- scale: Pops in with scale (impact)
- typewriter: Characters appear sequentially

**Position presets:**
- center: Hero text, statements
- top, bottom: Titles, captions
- top-left, top-right, bottom-left, bottom-right: Corners

**Font size guidelines:**
- 24-32px: Captions
- 36-48px: Feature callouts
- 56-72px: Headlines
- 80-120px: Hero text (single words)

## Interpreting Creative Notes

**"Make it magical / enhanced / glowing"**
→ Consider generating an AI-enhanced version
→ Crossfade from original to enhanced (opacity animation)

**"Add 'X' text that types in"**
→ Text layer with typewriter animation
→ Figure out when it should appear (startFrame)

**"Quick / energetic / punchy"**
→ Faster animations, spring easing
→ Maybe skip fade transitions (hard cuts)

**"Calm / confident / let it breathe"**
→ Slower transforms, ease_out
→ Longer duration, subtle zoom

**"Hero moment / premium / aha"**
→ Multiple layers, rich composition
→ Text that emphasizes the message
→ Careful timing

## Your Tools

1. `generate_enhanced_image(task_id, prompt, source_asset_path)`
   - Call this FIRST if you need AI-enhanced visuals
   - Returns a generated_asset_id to use in your layer
   
2. `submit_clip_spec(task_id, layers_json, enter_transition, exit_transition, notes)`
   - Call this LAST with your complete layer composition
   - layers_json is a JSON STRING of the array

## Process

1. Read the creative notes carefully
2. Decide what layers you need:
   - Always have the base image layer (unless notes say otherwise)
   - Add generated layer if notes mention enhancement
   - Add text layer if notes mention text
3. If generating, call generate_enhanced_image first
4. Build your layers array
5. Submit with submit_clip_spec

Think step by step:
1. What's the feeling/energy described?
2. Do I need AI generation for enhancement?
3. What text should appear, when, and how?
4. How do the layers work together?
5. What transitions between layers?

## Example Composition

Creative notes: "Hero moment - magical feel. Start plain, crossfade to glowing version. 'FOCUS' types in at center."

Thinking:
- Base layer: original screenshot, fades out
- Generated layer: glowing version, fades in
- Text layer: "FOCUS", typewriter animation, appears mid-clip

Layers:
```json
[
  {{
    "type": "image",
    "src": "screenshot.png",
    "zIndex": 1,
    "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.15, "easing": "ease_out"}},
    "opacity": {{"start": 1, "end": 0}}
  }},
  {{
    "type": "generated_image",
    "generatedAssetId": "xxx",
    "zIndex": 2,
    "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.15, "easing": "ease_out"}},
    "opacity": {{"start": 0, "end": 1}}
  }},
  {{
    "type": "text",
    "content": "FOCUS",
    "zIndex": 3,
    "style": {{"fontSize": 80, "fontWeight": 800, "color": "#FFFFFF"}},
    "animation": {{"enter": "typewriter", "exit": "fade", "enterDurationFrames": 20, "exitDurationFrames": 10}},
    "position": {{"preset": "center"}},
    "startFrame": 20,
    "durationFrames": 50
  }}
]
```
"""


def create_clip_composer_agent():
    """Create the clip composer React agent."""
    model = ChatGoogleGenerativeAI(
        model=Config.GEMINI_MODEL,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.3,  # More precise for technical work
    )
    
    return create_react_agent(
        model=model,
        tools=[submit_clip_spec, generate_enhanced_image],
        name="clip_composer",
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
    
    print(f"\n🎨 Composing clip {current_index + 1}/{len(pending_ids)}: {task.get('asset_path', 'generated-only')}")
    
    # Calculate frames
    fps = 30
    duration_frames = int(task["duration_s"] * fps)
    
    # Format prompt
    system_prompt = CLIP_COMPOSER_SYSTEM_PROMPT.format(
        asset_path=task["asset_path"] or "none (generate visuals)",
        duration_s=task["duration_s"],
        duration_frames=duration_frames,
        start_time_s=task["start_time_s"],
        composer_notes=task["composer_notes"],
    )
    
    # Create and run agent
    agent = create_clip_composer_agent()
    
    agent.invoke({
        "messages": [
            HumanMessage(content=system_prompt + f"\n\nTask ID: {task_id}\n\nCompose this clip now. If you need to generate enhanced visuals, do that first, then submit the complete spec.")
        ],
    })
    
    return {
        "current_clip_index": current_index + 1,
    }


def compose_all_clips_node(state: dict) -> dict:
    """
    Process all clips in one node (batch processing).
    """
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
        asset_display = task.get('asset_path', 'generated-only')
        print(f"\n   [{i}/{len(tasks)}] {asset_display}")
        
        duration_frames = int(task["duration_s"] * fps)
        
        system_prompt = CLIP_COMPOSER_SYSTEM_PROMPT.format(
            asset_path=task["asset_path"] or "none (generate visuals)",
            duration_s=task["duration_s"],
            duration_frames=duration_frames,
            start_time_s=task["start_time_s"],
            composer_notes=task["composer_notes"],
        )
        
        agent.invoke({
            "messages": [
                HumanMessage(content=system_prompt + f"\n\nTask ID: {task['id']}\n\nCompose this clip now.")
            ],
        })
    
    print(f"\n✓ All {len(tasks)} clips composed")
    return {}
