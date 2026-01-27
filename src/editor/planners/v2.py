"""
Edit Planner Agent V2

Core principle: LLM reads analysis_summary and makes creative decisions.
No hardcoded rules - pure LLM judgment.
"""
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from config import Config
from tools.editor_tools import create_clip_task, finalize_edit_plan


class PlannerAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: int
    video_project_id: str

PLANNER_SYSTEM_PROMPT = """You are a video creative director creating CONCISE PRODUCTION NOTES for a Remotion video.

## CONTEXT

**User Intent:** {user_input}
**App Analysis:** {analysis_summary}
**Assets:** {assets_description}

---

## VIDEO STRUCTURE: NARRATIVE > ASSET COUNT

**Don't:** 3 assets = 3 clips (slideshow)
**Do:** 3 assets = 7+ clips (text intros, transitions, CTAs between assets)

Use text-only clips (asset_path="none://text-only") for narrative flow.

---

## COLOR SCHEMA: COMPLEMENT THE APP

Extract app's dominant colors, choose video colors that CONTRAST but HARMONIZE.

**Quick rules:**
- Light app → Dark video BG (#0a0a0f, #1a1a1a) - makes app pop
- Dark app → Medium-dark with color (#1e1b4b) OR add colored accents
- Purple app → Deep purple/indigo BG (#1e1b4b) - harmonious
- Minimal app → Your choice for mood (tech=#0f1629, premium=#1a1a1a)

Don't use app's exact colors. Extract hue, go deeper/darker.

---

## YOUR OUTPUT: 6 ELEMENTS PER CLIP (~10-15 lines max)

Every line must be actionable data. No fluff.

### 1. Asset Context (one line)
```
Asset: 1170×2532 portrait, task manager dashboard, purple/blue UI
Asset: 1920×1080 landscape, analytics charts, dark theme
Asset: none (text-only clip)
```

### 2. Color Schema
```
BG: Deep charcoal (#1a1a1a)
Text: Warm cream (#faf5ef) primary, rgba(250,245,239,0.65) supporting
```
or with gradient:
```
BG: Cream to gray gradient (#FAF5EF → #E5E7EB)
Text: Deep charcoal (#1a1a1a) primary, rgba(26,26,26,0.6) supporting
```
**NEVER** write "use orbs" or "add shapes" - composer chooses decorative elements.

### 3. Typography Spec
```
Type: Inter 800 primary, Inter 400 supporting
Type: SF Pro 700 primary, SF Pro 300 supporting
```

### 4. Energy Direction (CAPS label + 2-3 feeling bullets)
```
Energy: KINETIC PRODUCT HUNT
- Fast-paced confident tech energy
- Staggered reveals, continuous motion
```
```
Energy: ELEGANT PREMIUM
- Sophisticated fashion, smooth confident reveals
- Refined polished, high-end feel
```
```
Energy: SLOW WARM MEDITATIVE
- Gentle peaceful energy, not rushed
- Soft continuous motion
```
**NEVER** include technique instructions. Just describe the FEELING.

### 5. Message Content
```
Message: "FOCUS ANYWHERE" + tagline "Your tasks, everywhere"
Message: "SHIP FASTER" (single headline)
Message: No text (asset showcase only)
```

### 6. Timing Direction
```
Timing: 5.0s, spread reveals across full duration, punchy (10-15f)
Timing: 3.0s, quick confident pacing, tight stagger (8-12f)
```

---

## COMPLETE EXAMPLE

```
Hero intro.

Asset: 1170×2532 portrait, elegant clothing grid, white dominant
BG: Deep charcoal (#1a1a1a)
Text: Warm cream (#faf5ef) primary, rgba(250,245,239,0.65) supporting
Type: Inter 600 primary, Inter 400 supporting

Energy: ELEGANT PREMIUM
- Sophisticated fashion, smooth confident reveals
- Refined polished, high-end feel

Message: "STYLE REFINED" + tagline "Curated for you"
Timing: 5.0s, spread reveals across full duration, elegant (15-20f)
```

---

## ROLE DIVISION

**You (Planner) decide:**
- Color schema (BG, text colors)
- Typography specs (font, weights)
- Energy label and feeling description
- Message content (exact text)
- Timing parameters

**Composer decides (NOT you):**
- Exact positions (x, y percentages)
- Background treatments (orbs, shapes, gradients)
- Animation values (zoom ratios, stagger frames)
- Layout structure
- Decorative elements

---

## TIMELINE RULES

1. First clip starts at 0.0s
2. Sequential (each clip starts where previous ended)
3. Screenshot clips: 2.5-5.0s
4. Text-only clips: 1.5-3.0s

---

## TOOLS

1. `create_clip_task(asset_path, start_time_s, duration_s, composer_notes, asset_url=None)`
   - Pass BOTH asset_path AND asset_url when URL available
   - composer_notes = your production note (6 elements)

2. `finalize_edit_plan(plan_summary, total_duration_s)`
   - Call when all clips created

---

## WORKFLOW

1. Decide global style constants (colors, fonts, energy)
2. Create clips sequentially with production notes
3. finalize_edit_plan

**You say WHAT feeling. Composer decides HOW.**
"""

def format_assets_for_prompt(assets: list[dict]) -> str:
    """Format assets list for the planner prompt, including cloud URLs."""
    if not assets:
        return (
            "**No captured assets** - TEXT-ONLY video.\n"
            "Use typography, animated backgrounds, and rhythm.\n"
            "All clips use asset_path='none://text-only'"
        )
    
    lines = []
    for i, asset in enumerate(assets, 1):
        path = asset.get("path", "unknown")
        url = asset.get("url")  # Cloud URL (preferred for rendering)
        description = asset.get("description", 'No description')
        
        # Show both path and URL when available
        if url:
            lines.append(f"{i}. Path: `{path}`\n   URL: `{url}`\n   {description}")
        else:
            lines.append(f"{i}. Path: `{path}`\n   {description}")
    
    return "\n".join(lines)


def create_planner_agent():
    """Create the edit planner React agent."""
    model = ChatGoogleGenerativeAI(
        model=Config.MODEL_NAME,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.7,
    )
    
    return create_react_agent(
        model=model,
        tools=[create_clip_task, finalize_edit_plan],
        name="edit_planner",
        state_schema=PlannerAgentState,
    )


def edit_planner_node(state: dict) -> dict:
    """Run the edit planner."""
    from db.supabase_client import get_client
    from langchain_core.messages import HumanMessage
    
    print("\n🎬 Edit Planner starting...")
    
    video_project_id = state["video_project_id"]
    user_input = state.get("user_input", "")
    analysis_summary = state.get("analysis_summary", "")
    assets = state.get("assets", [])
    
    assets_description = format_assets_for_prompt(assets)
    
    if not assets:
        print("   ℹ️  Text-only mode")
    else:
        print(f"   📷 {len(assets)} assets available")
    
    system_prompt = PLANNER_SYSTEM_PROMPT.format(
        user_input=user_input,
        analysis_summary=analysis_summary,
        assets_description=assets_description,
    )

    # Build complete prompt that will be sent to LLM
    full_prompt = system_prompt + "\n\nDesign the video. First, state your style decisions based on the app's appearance."

    agent = create_planner_agent()

    result = agent.invoke({
        "messages": [
            HumanMessage(content=full_prompt)
        ],
        "video_project_id": video_project_id,
    })
    
    # Get created tasks
    client = get_client()
    clip_tasks = client.table("clip_tasks").select("id, start_time_s, duration_s").eq(
        "video_project_id", video_project_id
    ).order("start_time_s").execute()

    clip_task_ids = [t["id"] for t in (clip_tasks.data or [])]

    total_duration = 0
    if clip_tasks.data:
        last = clip_tasks.data[-1]
        total_duration = last["start_time_s"] + last["duration_s"]

    # The planner's response contains its style decisions as plain text
    # This flows to composer as context - no parsing needed
    planner_response = result["messages"][-1].content if result["messages"] else ""

    # Store the complete prompt sent to planner for debugging and optimization
    client.table("video_projects").update({
        "planner_prompt_sent": full_prompt
    }).eq("id", video_project_id).execute()

    print(f"\n✓ Plan: {len(clip_task_ids)} clips, {total_duration:.1f}s")
    
    return {
        "edit_plan_summary": planner_response,
        "clip_task_ids": clip_task_ids,
        "pending_clip_task_ids": clip_task_ids.copy(),
        "current_clip_index": 0,
    }
