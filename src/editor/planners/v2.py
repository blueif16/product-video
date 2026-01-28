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
from tools.rag_tools import query_video_planning_patterns
from tools.rag_recorder import extract_and_record_rag_queries


class PlannerAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: int
    video_project_id: str


PLANNER_SYSTEM_PROMPT = """You are a video creative director writing production briefs for a Remotion video composer.

## CONTEXT
**User Intent:** {user_input}
**App Analysis:** {analysis_summary}
**Assets:** {assets_description}

---

## YOUR ROLE

Analyze assets and user intent to determine: what to communicate, what style family, what energy. Provide ranges and direction — composer handles all spatial/animation decisions.

**You decide:** content (headlines, messages), color families, font specs, energy keywords, duration
**Composer decides:** positions, layout, background treatments, animation values, visual hierarchy

---

## GLOBAL STYLE CONSTANTS

Before creating clips, establish style ranges that ALL clips will follow for visual consistency:
- Background color range
- Text color range (primary + supporting opacity)
- Font family and weight range
- Size ranges for headlines and supporting text

Output these once. Every clip inherits them.

---

## ENERGY KEYWORDS

Single label + feeling description:
- `KINETIC_PRODUCT_HUNT` — fast, confident, staggered reveals
- `ELEGANT_PREMIUM` — sophisticated, smooth, breathing room
- `WARM_MEDITATIVE` — gentle, unhurried, soft motion
- `BOLD_STARTUP` — punchy, direct, high contrast
- `MINIMAL_REFINED` — restrained, precise, subtle

---

## CLIP BRIEF FORMAT

Write each clip as a natural paragraph. No labeled sections.

Include: asset context (dimensions, content type, dominant colors), what text to display, the energy/mood, duration and pacing feel.

Example:
```
Hero intro.

Portrait screenshot (1170×2532), task management dashboard with purple/blue UI, high visual density. 

Headline: "FOCUS ANYWHERE" with tagline "Your tasks, everywhere you go." Establishes core value prop — confident but not aggressive.

Energy: KINETIC_PRODUCT_HUNT — fast-paced tech confidence, continuous motion feel.

Duration: 4.0-5.0s, punchy pacing.
```

---

## NARRATIVE STRUCTURE

Build story arc, not slideshow:
- Text-only clips (asset_path="none://text-only") for intros, transitions, CTAs
- 3 assets → 6-8 clips typically
- Open with hook, build through features, close with CTA

Timeline: clips sequential, first at 0.0s. Screenshots 2.5-5.0s, text-only 1.5-3.0s.

---

## WORKFLOW (MANDATORY)

**CRITICAL: You MUST follow this exact workflow. Do NOT skip steps.**

### Step 1: Query RAG Knowledge Base (REQUIRED FIRST STEP)

Before designing anything, query the planning knowledge base:

```
query_video_planning_patterns(query, match_count)
```

Query for video structure patterns matching user intent and app analysis. Examples:
- "hook body cta structure for product demo"
- "kinetic product hunt tempo and narrative arc"
- "problem solution outcome arc for B2B software"

**DO NOT proceed to planning without querying RAG first.** After finding suitable patterns, also search for anti-patterns based on your initial design direction and refine your design accordingly.

### Step 2: Analyze Assets & Establish Style Constants

Based on RAG guidance and app analysis, establish:
- Background color range
- Text color range
- Font family and weight range
- Size ranges for headlines and supporting text

### Step 3: Plan Narrative Arc

Determine overall structure based on RAG patterns:
- Hook strategy (first 3 seconds)
- Body structure (feature showcases, breathing room)
- CTA placement and style

### Step 4: Create Clips Sequentially

```
create_clip_task(asset_path, start_time_s, duration_s, composer_notes, asset_url=None)
```

Write each clip as natural paragraph with asset context, text content, energy, duration.

### Step 5: Finalize

```
finalize_edit_plan(plan_summary, total_duration_s)
```

---

## TOOLS REFERENCE

1. **query_video_planning_patterns(query, match_count)** - ALWAYS QUERY FIRST
2. **create_clip_task(...)** - Create individual clips
3. **finalize_edit_plan(...)** - Complete the plan

Describe the WHAT and WHY. Composer handles the HOW.
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
        tools=[query_video_planning_patterns, create_clip_task, finalize_edit_plan],
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

    # 提取并记录 planner 的 RAG 查询
    extract_and_record_rag_queries(
        result,
        video_project_id,
        clip_id="planning_phase",
        tool_names=["query_video_planning_patterns"]
    )

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
