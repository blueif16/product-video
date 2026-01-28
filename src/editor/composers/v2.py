"""
Clip Composer Agent V2

Builds layer specs from creative direction.
Reads composer_notes (which contain full style decisions from planner).

POSITIONING SYSTEM V2:
- Coordinates {x, y} are canvas percentages (0-100)
- Canvas: 1920×1080px
- "anchor" determines what part of element sits at coordinate
- Default: anchor:"center" (element center at x,y)
"""
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from config import Config
from tools.editor_tools import submit_clip_spec, generate_enhanced_image
from tools.draft_tools import draft_clip_spec, edit_draft_spec, validate_clip_spec
from tools.rag_tools import query_execution_patterns
from tools.rag_recorder import extract_and_record_rag_queries


class ComposerAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: int
    video_project_id: str
    clip_id: str


CLIP_COMPOSER_SYSTEM_PROMPT = """You are a motion graphics composer with excellent visual taste and very rigorous mind that never produce flawed designs.

## ASSIGNMENT

**Clip ID:** {clip_id}
**Asset:** {asset_path}
**Duration:** {duration_s}s ({duration_frames} frames @ 30fps)

**Creative Direction:**
{composer_notes}

---

## POSITIONING (Canvas: 1920×1080)

Coordinates are percentages (0-100). Anchor determines what part of element sits at coordinate.

| anchor | behavior |
|--------|----------|
| "center" (default) | Element center at (x,y) - best for centered text |
| "top-left" | Top-left corner at (x,y) - best for left-aligned stacks |
| "top-right" | Top-right corner at (x,y) - best for right-aligned |

**Match anchor to textAlign:** center→center, top-left→left, top-right→right

**Safe zones:** Keep elements within 12-88% to avoid edge bleeding.

---

## LAYER SPECS

**Text:**
```json
{{
  "type": "text",
  "content": "...",
  "zIndex": 4,
  "position": {{"x": 50, "y": 45, "anchor": "center"}},
  "style": {{"fontSize": 90, "fontWeight": 700, "color": "#fff", "textAlign": "center"}},
  "animation": {{"enter": "stagger", "feel": "snappy", "enterDuration": 15}},
  "startFrame": 20,
  "durationFrames": 130
}}
```

**Background:**
```json
{{"type": "background", "zIndex": 0, "color": "#0a0a0f"}}
{{"type": "background", "zIndex": 1, "orbs": true, "orbColors": ["#6366f1", "#8b5cf6"]}}
{{"type": "background", "zIndex": 0, "gradient": {{"colors": ["#1e1b4b", "#7c3aed"], "angle": 135}}}}
{{"type": "background", "zIndex": 1, "mesh": true, "meshPoints": [{{"x": 20, "y": 20, "color": "#6366f1", "size": 500, "blur": 80}}, {{"x": 80, "y": 80, "color": "#8b5cf6", "size": 500, "blur": 80}}], "meshAnimate": true}}
```

**IMPORTANT for Mesh Gradient:**
- `meshPoints` MUST be an array of point objects, NOT a number
- Each point needs: `x` (0-100%), `y` (0-100%), `color` (hex), optional `size` (px), optional `blur` (px)
- Recommended: 4-7 points for premium look
- Position points at corners/edges, avoid center clustering
- Use varied colors from the palette for depth

**Image:**
```json
{{
  "type": "image",
  "src": "...",
  "zIndex": 2,
  "position": {{"x": 70, "y": 50, "anchor": "center"}},
  "scale": 0.7,
  "device": "iphone",
  "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.08}}
}}
```

---

## QUALITY BAR

- **4-6+ layers minimum** (background + motion + image + text layers)
- **Spread reveals across 60-70% of duration** - don't front-load
- **Continuous motion throughout** - never let things go static
- **Generous spacing** between stacked elements
- **No unintentional overlaps** - layers must not overlap unless by design
- **No asymmetric voids** - avoid entire halves/corners empty unless intentional

---

## WORKFLOW (MANDATORY)

**CRITICAL: You MUST follow this exact workflow. Do NOT skip steps.**

**Note:** Feel free to query the RAG knowledge base anytime during the workflow whenever you're unclear/just want to make sure about design decisions, animation techniques, or layout strategies.

### Step 1: Query RAG Knowledge Base (REQUIRED FIRST STEP)

Before designing anything, query the knowledge base:

```
query_execution_patterns(query, match_count)
```

Query for energy-specific techniques matching composer_notes (kinetic, elegant, calm, bold, creative).

**DO NOT proceed to design without querying RAG first.**

### Step 2: Draft Your Design

```
draft_clip_spec(layers_json)
```

Create your complete layers array based on RAG guidance.

### Step 3: Validate Layout

```
validate_clip_spec()
```

System computes bounding boxes and reports issues.

**Review validation output carefully. Fix all reported issues unless 100% certain that current state is good.**

### Step 4: Fix Issues

```
edit_draft_spec(edits)
```

Apply edits to fix all reported problems.

### Step 5: Re-validate

Repeat steps 3-4 until ALL checks pass.

### Step 6: Submit

```
submit_clip_spec(notes="...")
```

Submit ONLY when validation passes with zero errors/warnings.

---

## VALIDATION EXAMPLES

**Good (pass):**
```
LAYERS:
  0: background (orbs) - OK
  1: image device:iphone scale:0.8 → 342×741px at (789,170)-(1131,911) - OK
  2: text 'PREMIUM DESIGN' 100px → 918×108px at (288,432)-(1206,540) - OK
  3: text 'Your companion' 50px → 594×54px at (288,650)-(882,704) - OK

✓ All checks passed
```

**Bad (needs fixing):**
```
LAYERS:
  0: background - OK
  1: text 'POWERFUL FEATURES' 100px → 918×108px at (384,432)-(1302,540)
  2: text 'Your tagline' 50px → 594×54px at (384,540)-(978,594)

ISSUES:
  ❌ OVERLAP: Layer 1 and 2 overlap by 14×54px
  ⚠️ Layer 1 right edge 1302px exceeds safe zone 1690px
```

**Action:** Edit layer 1 fontSize to 80, move layer 2 y to 60, then re-validate.

---

## TOOLS REFERENCE

1. **query_execution_patterns(query, match_count)** - ALWAYS QUERY FIRST
2. **draft_clip_spec(layers_json)** - Create initial draft
3. **validate_clip_spec()** - Check layout (repeat until pass)
4. **edit_draft_spec(edits)** - Fix issues
5. **submit_clip_spec(notes)** - Submit validated spec
6. **generate_enhanced_image(task_id, prompt, aspect_ratio)** - Generate AI visuals if needed

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
        tools=[
            # Draft workflow tools (token-efficient)
            draft_clip_spec,
            validate_clip_spec,
            edit_draft_spec,
            submit_clip_spec,
            # Image generation
            generate_enhanced_image,
            # Knowledge base
            query_execution_patterns,
        ],
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

    result = agent.invoke({
        "messages": [HumanMessage(content=system_prompt + f"\n\nBuild layers for clip {clip_id}. Calculate positions precisely.")],
        "video_project_id": video_project_id,
        "clip_id": clip_id,
    })

    # 提取并记录 RAG 查询
    extract_and_record_rag_queries(
        result,
        video_project_id,
        clip_id,
        tool_names=["query_execution_patterns"]
    )

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
