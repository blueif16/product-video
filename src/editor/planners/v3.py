"""
Edit Planner Agent V3

Establishes design system first, then creates clips with content-focused notes.
"""
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from src.config import Config
from src.tools.editor_tools import create_design_system, create_clip_task, finalize_edit_plan
from src.tools.rag_tools import query_video_planning_patterns
from src.tools.rag_recorder import extract_and_record_rag_queries


class PlannerAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: int
    video_project_id: str

PLANNER_SYSTEM_PROMPT = """You are a video creative director writing production briefs for a Remotion composer.

## CONTEXT
**User Intent:** {user_input}
**App Analysis:** {analysis_summary}
**Assets:** {assets_description}

---

## YOUR ROLE

You decide: WHAT to communicate (headlines, messages, mood, energy, duration)
Composer decides: HOW to execute (positions, layouts, animations, spacing)

---

## WORKFLOW

### Step 1: Query RAG (REQUIRED)

```
query_video_planning_patterns(query, match_count)
```

Query for: narrative arc, tempo, clip functions. Query until you understand the structure.

### Step 2: Create Design System (REQUIRED)

```
create_design_system(design_system_text)
```

Establish ONE unified visual style for the entire video. Include:
- Style and mode (e.g., "KINETIC_PRODUCT_HUNT light mode")
- Color palette (Background, Headline, Subtext, Accent colors)
- Typography (Family, sizes, weights for Label/Headline/Subtext)
- Animation feel (snappy, smooth, elegant)
- Spacing rules reference

**Query RAG for contrast rules if light background. Don't guess hex codes.**

### Step 3: Create Clips

```
create_clip_task(asset_path, start_time_s, duration_s, composer_notes, asset_url=None)
```

composer_notes should focus on:
- Clip function (hook, feature_showcase, transition, cta)
- Content strategy (what message, why it matters)
- Asset usage (how to present the screenshot)
- Energy/pacing for this clip

**Do NOT repeat colors/typography in composer_notes - they're in design_system.**

### Step 4: Finalize

```
finalize_edit_plan(plan_summary, total_duration_s)
```

---

## TOOLS

1. **query_video_planning_patterns** — ALWAYS query first
2. **create_design_system** — Create unified visual style
3. **create_clip_task** — Create clips with content-focused notes
4. **finalize_edit_plan** — Complete plan
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
        url = asset.get("url")
        description = asset.get("description", 'No description')

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
        tools=[query_video_planning_patterns, create_design_system, create_clip_task, finalize_edit_plan],
        name="edit_planner",
        state_schema=PlannerAgentState,
    )


def edit_planner_node(state: dict) -> dict:
    """Run the edit planner."""
    from ...db.supabase_client import get_client
    from langchain_core.messages import HumanMessage

    print("\n🎬 Edit Planner V3 starting...")

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

    full_prompt = system_prompt + "\n\nDesign the video. Query RAG first, then create design_system, then create clips."

    agent = create_planner_agent()

    result = agent.invoke({
        "messages": [
            HumanMessage(content=full_prompt)
        ],
        "video_project_id": video_project_id,
    })

    extract_and_record_rag_queries(
        result,
        video_project_id,
        clip_id="planning_phase",
        tool_names=["query_video_planning_patterns"]
    )

    client = get_client()
    clip_tasks = client.table("clip_tasks").select("id, start_time_s, duration_s").eq(
        "video_project_id", video_project_id
    ).order("start_time_s").execute()

    clip_task_ids = [t["id"] for t in (clip_tasks.data or [])]

    total_duration = 0
    if clip_tasks.data:
        last = clip_tasks.data[-1]
        total_duration = last["start_time_s"] + last["duration_s"]

    planner_response = result["messages"][-1].content if result["messages"] else ""

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
