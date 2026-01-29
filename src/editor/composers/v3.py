"""
Clip Composer Agent V3

Reads design_system + composer_notes to build layers.
Design system provides visual consistency, composer_notes provide content strategy.
"""
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from src.config import Config
from src.tools.editor_tools import submit_clip_spec, generate_enhanced_image
from src.tools.draft_tools import draft_clip_spec, edit_draft_spec, validate_clip_spec
from src.tools.rag_tools import query_execution_patterns
from src.tools.rag_recorder import extract_and_record_rag_queries


class ComposerAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: int
    video_project_id: str
    clip_id: str


CLIP_COMPOSER_SYSTEM_PROMPT = """You are a motion graphics composer. Your job: translate creative direction into precise layer specs.

## ASSIGNMENT

**Clip ID:** {clip_id}
**Asset:** {asset_path}
**Duration:** {duration_s}s ({duration_frames} frames @ 30fps)

---

## DESIGN SYSTEM (UNIFIED VISUAL STYLE)

{design_system_text}

---

## COMPOSER NOTES (THIS CLIP'S CONTENT STRATEGY)

{composer_notes}

---

## CORE PRINCIPLE

**Design System = Colors, typography, animation feel (WHAT to use)**
**Composer Notes = Content strategy, energy, asset usage (WHAT to say)**
**RAG Knowledge Base = Layout, spacing, timing, contrast (HOW to execute)**

You MUST query RAG for execution details. NEVER invent spacing numbers, contrast values, or layout zones from imagination.

---

## CANVAS & POSITIONING

Canvas: 1920×1080. Coordinates are percentages (0-100).

| anchor | behavior |
|--------|----------|
| "center" | Element center at (x,y) |
| "top-left" | Top-left corner at (x,y) |

Safe zones: 12-88% to avoid edge bleeding.

---

## LAYER SPEC EXAMPLES

```json
{{"type": "text", "content": "...", "zIndex": 4, "position": {{"x": 50, "y": 45, "anchor": "center"}}, "style": {{"fontSize": 90, "fontWeight": 700, "color": "#fff", "textAlign": "center"}}, "animation": {{"enter": "stagger", "feel": "snappy", "enterDuration": 15}}, "startFrame": 20, "durationFrames": 130}}
```

```json
{{"type": "background", "zIndex": 0, "color": "#0a0a0f"}}
{{"type": "background", "zIndex": 1, "mesh": true, "meshPoints": [{{"x": 20, "y": 20, "color": "#6366f1", "size": 500, "blur": 80}}], "meshAnimate": true}}
```

```json
{{"type": "image", "src": "...", "zIndex": 2, "position": {{"x": 70, "y": 50, "anchor": "center"}}, "scale": 0.7, "device": "iphone", "transform": {{"type": "zoom_in", "startScale": 1.0, "endScale": 1.08}}}}
```

**meshPoints MUST be array of objects with x, y, color, size, blur — NOT a number.**

---

## WORKFLOW (MANDATORY)

### Step 1: Query RAG Until Complete Understanding

```
query_execution_patterns(query, match_count)
```

**Query for EVERY unknown:**
- Layout zones and spacing (horizontal split? vertical stack? → query it)
- Text contrast requirements (light bg? dark bg? → query it)
- Single-line headline sizing (how to calculate max width? → query it)
- Anchor/textAlign matching rules (→ query it)
- Temporal distribution of animations (→ query it)

**DO NOT PROCEED until you have concrete numbers from RAG for:**
- Exact x% zones for text vs image
- Exact gap percentages between elements
- Exact color hex codes for contrast
- Exact fontSize calculation for single-line headlines

**If first query doesn't give you numbers, QUERY AGAIN with more specific terms.**
**Your knowledge GROWS with each query. Query 3-5 times minimum.**

### Step 2: Draft with Design System + RAG Numbers

```
draft_clip_spec(layers_json)
```

- Colors/fonts from design_system
- Content/energy from composer_notes
- Layout/spacing from RAG

Use ONLY numbers and values from RAG. If RAG says "text zone x:12-48%", use x:12-48%, not x:50.

### Step 3: Validate

```
validate_clip_spec()
```

Fix ALL reported issues. Re-query RAG if unsure how to fix.

### Step 4: Fix & Re-validate

```
edit_draft_spec(edits)
```

Loop steps 3-4 until ALL checks pass.

**Common fixes:**
- Overlay too large: `[{{"layer_index": 1, "field_path": "meshPoints[0].size", "value": 250}}]`
- Text bleed: `[{{"layer_index": 2, "field_path": "position.y", "value": 45}}]`
- Font size: `[{{"layer_index": 2, "field_path": "style.fontSize", "value": 100}}]`

**Array indexing:** Use `meshPoints[0].size` to edit array elements.

### Step 5: Submit

```
submit_clip_spec(notes="...")
```

---

## QUALITY = DESIGN SYSTEM + RAG COMPLIANCE

- **Colors/Fonts:** Design system tells you exact values. Use them.
- **Spacing:** RAG tells you exact zones. Follow them.
- **Contrast:** RAG tells you exact hex codes. Use them.
- **Headlines:** RAG tells you max-width formula. Calculate it.
- **Alignment:** RAG tells you anchor/textAlign rules. Match them.
- **Motion:** RAG tells you temporal distribution. Spread reveals accordingly.

**If something looks wrong, the answer is in RAG. Query again.**

---

## TOOLS

1. **query_execution_patterns(query, match_count)** — YOUR PRIMARY TOOL. Use repeatedly.
2. **draft_clip_spec(layers_json)** — Create draft
3. **validate_clip_spec()** — Check layout
4. **edit_draft_spec(edits)** — Fix issues
5. **submit_clip_spec(notes)** — Submit when valid
6. **generate_enhanced_image(...)** — AI visuals if needed
"""


def create_clip_composer_agent():
    """Create the clip composer React agent with retry logic."""
    model = ChatGoogleGenerativeAI(
        model=Config.MODEL_NAME,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.3,
        timeout=120,
        max_retries=3,
    )

    return create_react_agent(
        model=model,
        tools=[
            draft_clip_spec,
            validate_clip_spec,
            edit_draft_spec,
            submit_clip_spec,
            generate_enhanced_image,
            query_execution_patterns,
        ],
        name="clip_composer",
        state_schema=ComposerAgentState,
    )


def compose_single_clip_node(state: dict) -> dict:
    """Compose ONE clip. For parallel execution via Send."""
    from ...db.supabase_client import get_client
    from langchain_core.messages import HumanMessage
    from src.tools.storage import resolve_asset_src
    import traceback

    clip_id = state["clip_id"]
    video_project_id = state["video_project_id"]

    client = get_client()

    try:
        result = client.table("clip_tasks").select("*").eq("id", clip_id).single().execute()
        task = result.data

        if not task:
            print(f"   ⚠️  Clip {clip_id} not found")
            return {}

        # Read design_system
        project = client.table("video_projects").select("design_system_text").eq(
            "id", video_project_id
        ).single().execute()
        design_system_text = project.data.get("design_system_text", "")

        if not design_system_text:
            print(f"   ⚠️  No design_system found for project {video_project_id}")
            design_system_text = "No design system provided. Use default styling."

        asset_src = resolve_asset_src(task.get("asset_url"), task.get("asset_path"))
        print(f"\n   [{clip_id[:8]}] {asset_src}")

        fps = 30
        duration_frames = int(task["duration_s"] * fps)

        system_prompt = CLIP_COMPOSER_SYSTEM_PROMPT.format(
            clip_id=clip_id,
            asset_path=asset_src,
            duration_s=task["duration_s"],
            duration_frames=duration_frames,
            design_system_text=design_system_text,
            composer_notes=task["composer_notes"],
        )

        agent = create_clip_composer_agent()

        result = agent.invoke({
            "messages": [HumanMessage(content=system_prompt + f"\n\nBuild layers for clip {clip_id}. Query RAG first for layout patterns, spacing rules, and contrast requirements. Then draft.")],
            "video_project_id": video_project_id,
            "clip_id": clip_id,
        })

        extract_and_record_rag_queries(
            result,
            video_project_id,
            clip_id,
            tool_names=["query_execution_patterns"]
        )

        return {}

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        error_trace = traceback.format_exc()

        if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            print(f"   ⚠️  API quota/rate limit hit for clip {clip_id[:8]}")
            error_category = "quota_exceeded"
        elif "timeout" in error_msg.lower():
            print(f"   ⏱️  Timeout for clip {clip_id[:8]}")
            error_category = "timeout"
        elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
            print(f"   🔑 API auth error for clip {clip_id[:8]}")
            error_category = "auth_error"
        elif "subscriptable" in error_msg.lower():
            print(f"   🐛 SDK bug for clip {clip_id[:8]} (known issue)")
            error_category = "sdk_bug"
        else:
            print(f"   ❌ Clip {clip_id[:8]} failed: {error_type}: {error_msg[:100]}")
            error_category = "unknown"

        try:
            client.table("clip_tasks").update({
                "status": "failed",
                "clip_spec": {
                    "error": f"{error_type}: {error_msg}",
                    "error_category": error_category,
                    "traceback": error_trace[:1000]
                }
            }).eq("id", clip_id).execute()
        except Exception as db_error:
            print(f"   ⚠️  Failed to update error status: {db_error}")

        return {}


def compose_all_clips_node(state: dict) -> dict:
    """Compose all clips sequentially."""
    from src.tools.editor_tools import get_pending_clip_tasks

    video_project_id = state["video_project_id"]
    tasks = get_pending_clip_tasks(video_project_id)

    if not tasks:
        print("   ✓ No pending clip tasks")
        return {}

    print(f"\n🎨 Composing {len(tasks)} clips (V3)...")

    success_count = 0
    failed_count = 0

    for i, task in enumerate(tasks, 1):
        asset_display = task.get('asset_path') or 'text-only'
        if len(asset_display) > 50:
            asset_display = "..." + asset_display[-47:]
        print(f"\n   [{i}/{len(tasks)}] {asset_display}")

        try:
            compose_single_clip_node({
                "clip_id": task["id"],
                "video_project_id": video_project_id,
            })
            success_count += 1
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Unexpected error in clip {task['id'][:8]}: {e}")
            continue

    print(f"\n✓ Composition complete: {success_count} succeeded, {failed_count} failed")
    return {}
