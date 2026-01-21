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
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from config import Config
from tools.editor_tools import create_clip_task, finalize_edit_plan


# ─────────────────────────────────────────────────────────────
# Planner Prompt
# ─────────────────────────────────────────────────────────────

PLANNER_SYSTEM_PROMPT = """You are a creative director designing a modern product video.

## Your Context

**User's Vision:**
{user_input}

**Analysis (what we know about the app):**
{analysis_summary}

**Available Assets:**
{assets_description}

## Your Mission

Design a compelling video timeline by creating "moments" (clip_tasks).

Each moment is a creative unit that can have:
- The original screenshot/recording
- AI-enhanced visual versions (the composer can generate these)
- Text overlays
- Transitions between visual states

Your job is to DESCRIBE what each moment should feel like.
The composer will figure out HOW to achieve it technically.

## Modern Product Video Philosophy

- Visual rhythm over narrative structure
- Rapid sequences with breathing room
- Creative freedom (not rigid hook/demo/CTA)
- Layers of visual interest
- Moments that transform (plain → enhanced → text)

## Example Creative Thinking

"I'll open with the dashboard, but make it MAGICAL. Start plain, then have it
transform with a glowing AI-enhanced version. 'FOCUS' text types in dramatically.
Slow zoom to the task counter. This is the hero moment - needs to feel premium."

"Quick feature flash - swipe gesture recording. Keep it raw and energetic.
Add bold 'SWIPE' text that slides with the motion. No fancy enhancements here,
just pure speed and satisfaction."

"Transition moment - use an AI-generated abstract gradient background.
No screenshot, just a beautiful transition visual. 'NEVER FORGET' fades in
centered. Brief pause before the next feature."

## Tool: create_clip_task

```
create_clip_task(
    asset_path,      # Path to screenshot/recording (or "none" for generated-only moments)
    start_time_s,    # When this moment starts
    duration_s,      # How long it lasts
    composer_notes   # YOUR FULL CREATIVE VISION
)
```

### Composer Notes - Be Rich and Descriptive!

The composer reads your notes and decides what layers to create.
Tell them EVERYTHING about your vision:

**Good notes (rich creative intent):**

"Hero moment - make this MAGICAL. Start with the plain dashboard screenshot,
hold for 0.3s, then crossfade to an AI-enhanced version with subtle purple/blue
glow effects around the UI elements. Add 'NEVER FORGET' text that types in
character by character starting at 0.5s - big, bold, white, center of screen.
Slow zoom towards the task counter in the upper right. Premium, confident energy.
This is the 'aha' moment."

"Quick action flash - energetic montage feel. Use the swipe recording as-is,
but add 'COMPLETE' text that slides in from the right in sync with the gesture.
Fast, punchy. Maybe slight zoom in. No need for AI enhancement here - the
motion of the gesture IS the visual interest."

"Breathing room - pure visual moment. Generate a beautiful abstract gradient
background (purples and teals, flowing). No screenshot. Just atmosphere.
'Simple. Powerful.' fades in at center. Brief pause. Sets up the next feature."

**Bad notes (too sparse):**

"Zoom in on dashboard" — no feel, no layers, no vision
"Show the app" — doesn't inspire composition
"Add title" — which title? what style? where? when?

## Important

- Each moment is self-contained (has its own layers)
- You CAN have moments with no screenshot (generated visuals only)
- Text is PART of the moment, not separate
- Think about TRANSFORMATIONS within moments (plain → enhanced)
- DON'T worry about music (music comes later, adapts to you)
- DO think about visual rhythm and pacing
- DO be specific about the FEEL of each moment

## Timeline Planning Tips

- Hero moments: 2-4 seconds (let them breathe)
- Feature flashes: 0.8-1.5 seconds (quick hits)
- Transition/breathing: 0.5-1 second (visual palette cleanser)
- Consider starting with impact, building rhythm, ending with CTA

Design the video, create the tasks, then finalize.
"""


def format_assets_for_prompt(assets: list[dict]) -> str:
    """Format assets list for the planner prompt."""
    if not assets:
        return "No assets available - you can create moments with AI-generated visuals only."
    
    lines = []
    for i, asset in enumerate(assets, 1):
        capture_type = asset.get("capture_type", "unknown")
        emoji = "📸" if capture_type == "screenshot" else "🎬"
        path = asset.get("path", "unknown")
        description = asset.get("description", 'No description')
        validation = asset.get("validation_notes", 'N/A')
        
        lines.append(
            f"{i}. {emoji} `{path}`\n"
            f"   {description}\n"
            f"   Quality: {validation}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Agent Creation
# ─────────────────────────────────────────────────────────────

def create_planner_agent():
    """Create the edit planner React agent."""
    model = ChatGoogleGenerativeAI(
        model=Config.GEMINI_MODEL,
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
    
    system_prompt = PLANNER_SYSTEM_PROMPT.format(
        user_input=user_input,
        analysis_summary=analysis_summary,
        assets_description=assets_description,
    )
    
    # Create and run agent
    agent = create_planner_agent()
    
    result = agent.invoke({
        "messages": [
            HumanMessage(content=system_prompt + "\n\nDesign the video now. Create your moments (clip_tasks), then finalize the plan.")
        ],
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
