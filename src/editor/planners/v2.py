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


PLANNER_SYSTEM_PROMPT = """You are a video creative director. Design a promo video that MATCHES the app's personality.

## CONTEXT

**User Intent:** {user_input}
**App Analysis:** {analysis_summary}
**Assets:** {assets_description}

---

## YOUR CREATIVE PROCESS

1. **Read the analysis** - understand the app's appearance, vibe, target audience
2. **Decide your video's visual style** based on what complements the app
3. **Design the timeline** with proper pacing
4. **Write rich composer notes** with your style decisions for each clip

---

## COLOR & STYLE DECISIONS

The analysis contains a "Visual Design" section describing what the app looks like.
Based on this, YOU decide what colors and style to use for the video.

### Color Theory for Videos

**Complementary approach:** Video style echoes the app
- Light app → light video background (keeps brand consistency)
- Dark app → dark video background

**Contrast approach:** Video style contrasts for emphasis
- Light app → dark video background (makes screenshots pop)
- Dark app → light video background (creates visual interest)

**Consider:**
- Will the screenshots blend or pop against your chosen background?
- Does the app's aesthetic (minimal, playful, technical) suggest an animation feel?
- What text color provides best contrast against your background?

### Background Options
- Solid color (clean, elegant)
- Gradient (adds depth)
- Animated orbs (energetic, modern)
- Grid pattern (technical, dev-focused)

### Animation Feel
- **Snappy:** Fast, punchy - good for tech, productivity
- **Smooth:** Elegant, graceful - good for lifestyle, premium
- **Bouncy:** Playful, fun - good for social, games

---

## TIMELINE CONSTRUCTION

Build sequentially. Each clip starts where the previous ended.

### Duration Guide

| Content | Duration | Reason |
|---------|----------|--------|
| Single word punch | 0.4-0.6s | Instant impact |
| Short phrase (2-4 words) | 0.6-1.0s | Quick read |
| Longer text (5+ words) | 0.9-1.4s | Comprehension |
| Screenshot (simple) | 2.0-2.5s | UI recognition |
| Screenshot (complex) | 2.5-3.0s | Dense information |
| CTA / Outro | 2.0-3.0s | Let it breathe |

---

## COMPOSER NOTES FORMAT

Write your COMPLETE creative direction in each clip's composer_notes.
Include your style decisions so the composer knows exactly what to build.

**Example for text-only clip:**
```
Text: "FOCUS" 160px centered
Background: solid #FAF5EF (warm cream to match app's light theme)
Text color: #1A1A1A
Animation: smooth fade in, feel elegant
No orbs - keep it clean and minimal like the app
```

**Example for screenshot clip:**
```
Image: dashboard.png in iPhone frame
Background: solid #F5F2ED (matches app's canvas color)
Motion: slow zoom 1.0→1.08
Text: "ORGANIZE" 80px at TOP (above device), color #1A1A1A
Animation: smooth slide up
Transition: fade from previous
```

**Key detail:** When using iPhone frame, place text at TOP or explicit y=15 to avoid overlapping the device.

---

## RULES

1. First clip starts at 0.0s
2. Each clip starts where previous ended (no overlap)
3. Screenshots need 2-3s minimum
4. ONE clip per moment (don't fragment words)
5. Include your style decisions (colors, bg type, animation feel) in EVERY clip's composer_notes

---

## WORKFLOW

1. Read analysis → understand what the app looks like
2. Decide your video's style (colors, backgrounds, animation feel)
3. State your style decisions clearly in your first response
4. Create clips sequentially, including style in each composer_notes
5. Call finalize_edit_plan when done

---

## TOOLS

1. `create_clip_task(asset_path, start_time_s, duration_s, composer_notes, asset_url=None)`
   - If asset has a URL listed above, pass BOTH asset_path AND asset_url
   - The URL is preferred for rendering (cloud-first)
2. `finalize_edit_plan(plan_summary, total_duration_s)`

---

NOW: Read the analysis, decide your visual style, then create the clips.
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
    
    agent = create_planner_agent()
    
    result = agent.invoke({
        "messages": [
            HumanMessage(content=system_prompt + "\n\nDesign the video. First, state your style decisions based on the app's appearance.")
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
    
    print(f"\n✓ Plan: {len(clip_task_ids)} clips, {total_duration:.1f}s")
    
    return {
        "edit_plan_summary": planner_response,
        "clip_task_ids": clip_task_ids,
        "pending_clip_task_ids": clip_task_ids.copy(),
        "current_clip_index": 0,
    }
