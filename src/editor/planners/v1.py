"""
Edit Planner Agent

The creative director. Designs the video timeline by creating clip_tasks.
Each clip_task is a "moment" that can contain multiple layers (images,
generated images, text) - the composer decides the specifics.

The planner's job is to:
1. Understand the user's vision and the available assets
2. Design the pacing and flow of the video
3. Write rich creative direction for each moment
"""
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from config import Config
from tools.editor_tools import create_clip_task, finalize_edit_plan


# ─────────────────────────────────────────────────────────────
# Custom State Schema for InjectedState
# ─────────────────────────────────────────────────────────────

class PlannerAgentState(TypedDict):
    """
    Extended state schema for the planner agent.
    
    This allows tools using InjectedState to access video_project_id.
    The messages field uses add_messages reducer (required by create_react_agent).
    remaining_steps is required by create_react_agent for iteration control.
    """
    messages: Annotated[list, add_messages]
    remaining_steps: int  # Required by create_react_agent
    video_project_id: str


# ─────────────────────────────────────────────────────────────
# Planner Prompt
# ─────────────────────────────────────────────────────────────

PLANNER_SYSTEM_PROMPT = """You design video timelines. Create clips with specific text, sizes, and animations.

## ENERGY

This is a Product Hunt video. Every clip PUNCHES. It's a highlight reel, not a story.
Cut BEFORE the viewer gets comfortable. If it feels calm, make it faster.

## Context

**User Input:** {user_input}
**Analysis:** {analysis_summary}
**Assets:** {assets_description}

## TIMING

| Type | Duration |
|------|----------|
| Single word | 0.4-0.6s |
| Phrase (2-4 words) | 0.6-1.0s |
| Screenshot + text | 0.8-1.2s |
| Hero/brand | 1.2-1.8s |

Max: 2 seconds per clip. Target: 1.3 clips per second.

## TEXT SIZES

| Type | Size |
|------|------|
| Hero word | 160px |
| Brand name | 140px |
| Key phrase | 90px |
| Supporting | 60px |

## TOOL

```
create_clip_task(asset_path, start_time_s, duration_s, composer_notes)
```

asset_path: Screenshot path or "none://text-only"

## COMPOSER NOTES FORMAT

Write exactly what to render. Include:
- Text content in quotes
- Size in px
- Animation type + duration in frames
- Position (ALWAYS use preset "center" for centered text, NEVER use custom x/y)
- Background color (for text-only)

**Single word (0.5s):**
```
Text: "FAST" 160px white centered
Animation: scale 6 frames, feel: snappy
Background: #0a0a0f
Exit: none (hard cut)
```

**Two lines staggered (0.9s):**
```
Line 1: "From idea" 80px white, preset center with y=42%, frame 0
Line 2: "to launch." 80px #a5b4fc, preset center with y=58%, frame 10
Animation: fade 6 frames each, feel: smooth
Background: #0f172a
Exit: fade 4 frames
```

**Bilingual text (elegant, calm):**
```
English: "Your Daily Guide" 72px #78350f, preset center with y=45%
Chinese: "每日指南" 64px #f59e0b, preset center with y=55%
Animation: fade 12 frames, feel: smooth
Background: gradient #fef3c7 → #fde68a
Exit: fade 8 frames
```

**Screenshot + overlay (0.8s):**
```
Image: dashboard.png, iPhone frame
Zoom: 1.0→1.06
Text: "ORGANIZE" 90px white bottom-center
Text animation: slide_up 8 frames
```

**Typewriter hero (1.5s):**
```
Text: "STREAMLINE" 180px white centered
Animation: typewriter 2 frames/char
Background: #030712 with purple orbs
```

## 10-SECOND EXAMPLE

```
0.0-0.5s: "BUILD" 160px scale center
0.5-1.0s: "SHIP" 160px scale center  
1.0-1.5s: "GROW" 160px scale center
1.5-2.3s: "The fastest way" 70px fade
2.3-3.0s: "to launch" 70px fade
3.0-3.7s: "Zero config" 90px slide_up
3.7-4.4s: "Zero friction" 90px slide_up
4.4-5.1s: "Zero waiting" 90px slide_up
5.1-6.2s: "From commit to production" 60px
6.2-7.0s: "in seconds." 100px scale
7.0-8.3s: "STREAMLINE" 180px typewriter
8.3-10.0s: "Start free →" 90px fade
```

12 clips. Each has: text, size, animation, timing.

## RULES

1. No clip > 2 seconds
2. Every note has: text + size + animation + position
3. Hero text ≥ 140px
4. Phrase text ≥ 70px
5. First clip is a PUNCH (single big word, scale animation)
6. Last clip is CTA or brand
7. Prefer hard cuts (exit: none) over fade-outs for energy

Create clips now. Then call finalize_edit_plan.
"""


def format_assets_for_prompt(assets: list[dict]) -> str:
    """Format assets list for the planner prompt."""
    if not assets:
        return (
            "**No assets available** - This is a TEXT-ONLY video.\n\n"
            "Create moments using:\n"
            "- Background layers (gradients, animated orbs)\n"
            "- Text layers with dramatic animations\n"
            "- Use asset_path='none://text-only' for all clips\n\n"
            "Focus on typography, visual rhythm, and the user's messaging."
        )
    
    lines = []
    for i, asset in enumerate(assets, 1):
        path = asset.get("path", "unknown")
        description = asset.get("description", 'No description')
        
        # Description now includes [dimensions, type] suffix
        lines.append(f"{i}. `{path}`\n   {description}")
    
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Agent Creation
# ─────────────────────────────────────────────────────────────

def create_planner_agent():
    """
    Create the edit planner React agent with custom state schema.
    
    Uses PlannerAgentState to make video_project_id available to tools
    via InjectedState annotation.
    """
    model = ChatGoogleGenerativeAI(
        model=Config.MODEL_NAME,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.7,  # More creative
    )
    
    tools = [
        create_clip_task,
        finalize_edit_plan,
    ]
    
    return create_react_agent(
        model=model,
        tools=tools,
        name="edit_planner",
        state_schema=PlannerAgentState,  # Custom schema with video_project_id
    )


# ─────────────────────────────────────────────────────────────
# Node Function
# ─────────────────────────────────────────────────────────────

def edit_planner_node(state: dict) -> dict:
    """
    LangGraph node: Run the edit planner.
    
    Reads context from state, creates clip_tasks in DB,
    returns updated state with task IDs.
    """
    from db.supabase_client import get_client
    from langchain_core.messages import HumanMessage
    
    print("\n🎬 Edit Planner starting...")
    
    video_project_id = state["video_project_id"]
    user_input = state.get("user_input", "")
    analysis_summary = state.get("analysis_summary", "")
    assets = state.get("assets", [])
    
    # Format the prompt
    assets_description = format_assets_for_prompt(assets)
    
    # Note if text-only
    if not assets:
        print("   ℹ️  Text-only mode (no captured assets)")
    
    system_prompt = PLANNER_SYSTEM_PROMPT.format(
        user_input=user_input,
        analysis_summary=analysis_summary,
        assets_description=assets_description,
    )
    
    # Create and run agent
    agent = create_planner_agent()
    
    # IMPORTANT: Pass state keys that tools need via InjectedState
    # The agent invocation needs access to video_project_id for tools to work
    result = agent.invoke({
        "messages": [
            HumanMessage(content=system_prompt + "\n\nDesign the video now. Create your moments (clip_tasks), then finalize the plan.")
        ],
        # State keys required by tools (InjectedState)
        "video_project_id": video_project_id,
    })
    
    # Get created task IDs from DB
    client = get_client()
    
    clip_tasks = client.table("clip_tasks").select("id").eq(
        "video_project_id", video_project_id
    ).execute()
    
    clip_task_ids = [t["id"] for t in (clip_tasks.data or [])]
    
    # Extract plan summary from the final message
    final_message = result["messages"][-1].content if result["messages"] else ""
    
    print(f"\n✓ Plan created: {len(clip_task_ids)} moments")
    
    return {
        "edit_plan_summary": final_message,
        "clip_task_ids": clip_task_ids,
        "pending_clip_task_ids": clip_task_ids.copy(),
        "current_clip_index": 0,
    }
