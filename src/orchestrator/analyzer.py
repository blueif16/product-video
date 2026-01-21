"""
Analyzer node: Domain expert. OWNS all video production decisions.

- Reads user_input directly to understand intent
- Explores codebase to understand the app
- Builds structured app_manifest (bundle_id, screens, tabs, deep_links)
- Forms expert opinion on what to capture
- Creates tasks based on ITS judgment
- Writes comprehensive analysis for downstream phases
"""
from typing import Optional
import json

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

from config import get_model
from tools import ANALYZER_TOOLS
from db.supabase_client import create_task, create_video_project
from .state import PipelineState, AppManifest
from .session import get_session


# ─────────────────────────────────────────────────────────────
# Context
# ─────────────────────────────────────────────────────────────

class AnalyzerContext:
    """Context for analyzer to accumulate its work."""
    def __init__(self):
        self.analysis_summary: Optional[str] = None
        self.tasks_created: int = 0
        self.task_ids: list[str] = []
        self.app_manifest: Optional[AppManifest] = None

_ctx = AnalyzerContext()


def reset_context():
    global _ctx
    _ctx = AnalyzerContext()


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────

def create_tools(app_bundle_id: str, url_schemes: list[str]):
    """Create tools for the analyzer agent."""
    
    @tool
    def set_app_manifest(
        app_name: str,
        app_description: str,
        screens_json: str,
        tab_structure_json: str = "[]",
        navigation_notes: str = ""
    ) -> str:
        """
        Define the structured app manifest. Call this AFTER exploring the codebase.
        
        This manifest flows to all downstream agents (capturer, validator) so they
        know what screens exist, how to navigate, and what the app looks like.
        
        Args:
            app_name: Human-readable app name (e.g., "Yiban")
            app_description: What the app does (1-2 sentences for validator context)
            screens_json: JSON array of screens, each with:
                - name: Screen name (e.g., "Home", "Closet")
                - description: What this screen shows (for validator)
                - tab_index: (optional) Which tab, 0-indexed
                - deep_link: (optional) Deep link to this screen
                Example: '[{"name": "Home", "description": "Weather-based outfit suggestion", "tab_index": 0}]'
            tab_structure_json: JSON array of tab names in order (e.g., '["Home", "Closet", "Outfits"]')
            navigation_notes: Any notes about navigation quirks
        
        Returns:
            Confirmation
        """
        try:
            screens = json.loads(screens_json)
            tabs = json.loads(tab_structure_json)
        except json.JSONDecodeError as e:
            return f"ERROR: Invalid JSON - {e}"
        
        _ctx.app_manifest = AppManifest(
            bundle_id=app_bundle_id,
            app_name=app_name,
            url_schemes=url_schemes,
            screens=screens,
            tab_structure=tabs,
            navigation_notes=navigation_notes,
            app_description=app_description,
        )
        
        return f"App manifest set: {app_name} with {len(screens)} screens, {len(tabs)} tabs"
    
    @tool
    def create_capture_task(description: str, capture_type: str, target_screen: str = "") -> str:
        """
        Create a capture task in the database.
        
        Args:
            description: Full description - what to capture, how to navigate,
                        what makes a good capture. Be detailed.
            capture_type: "screenshot" or "recording"
            target_screen: Which screen from app_manifest this captures (for reference)
        
        Returns:
            Confirmation with task ID
        """
        ctype = "recording" if "record" in capture_type.lower() else "screenshot"
        
        # Enrich description with target screen info
        full_description = description
        if target_screen:
            full_description = f"[Target: {target_screen}]\n\n{description}"
        
        task_id = create_task(
            app_bundle_id=app_bundle_id,
            task_description=full_description,
            capture_type=ctype
        )
        _ctx.tasks_created += 1
        _ctx.task_ids.append(task_id)
        
        # Track in session for cleanup on interrupt
        session = get_session()
        session.add_task(task_id)
        
        return f"Created {ctype} task #{_ctx.tasks_created}: {task_id[:8]}..."
    
    @tool
    def finalize_analysis(analysis_summary: str) -> str:
        """
        Finalize your analysis with a complete summary of your video strategy.
        
        Call this AFTER setting app_manifest and creating all capture tasks.
        
        Args:
            analysis_summary: Your complete analysis and strategy, including:
                - Your understanding of what the user wants
                - Why you chose these specific captures
                - How they should fit together (pacing, flow, story)
                - Any important notes for editing
        
        Returns:
            Confirmation
        """
        _ctx.analysis_summary = analysis_summary
        return f"Analysis finalized. {_ctx.tasks_created} tasks created."
    
    return [set_app_manifest, create_capture_task, finalize_analysis]


# ─────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────

def analyze_and_plan_node(state: PipelineState) -> dict:
    """Analyzer node: explores codebase, builds manifest, creates tasks."""
    reset_context()
    print(f"\n🔍 Analyzing project...")
    
    # Update session state
    session = get_session()
    session.current_stage = "analyzing"
    
    app_bundle_id = state.get("app_bundle_id", "com.app.unknown")
    session.app_bundle_id = app_bundle_id
    
    # Get URL schemes from state (extracted by intake)
    url_schemes = state.get("url_schemes", [])
    
    tools = ANALYZER_TOOLS + create_tools(app_bundle_id, url_schemes)
    
    # Build context about known URL schemes
    url_scheme_info = ""
    if url_schemes:
        url_scheme_info = f"\nKNOWN URL SCHEMES: {', '.join(url_schemes)} (use these for deep links)"
    
    agent = create_react_agent(
        model=get_model(),
        tools=tools,
        name="analyzer",
        prompt=f"""You are an expert iOS developer AND video producer.

USER'S REQUEST:
{state['user_input']}

PROJECT PATH: {state['project_path']}
BUNDLE ID: {app_bundle_id}{url_scheme_info}

YOUR TOOLS:
- list_directory, read_file, run_bash: Explore the codebase
- set_app_manifest: Define app structure (screens, tabs, deep links) - CALL THIS FIRST after exploring
- create_capture_task: Create a task for something worth capturing
- finalize_analysis: Write your complete strategy (call this LAST)

YOUR JOB (in order):

1. EXPLORE the codebase - understand the app's structure
   - Look for View files, TabView, NavigationStack
   - Identify main screens and their purposes
   - Find any deep link handlers (URL schemes)

2. SET APP MANIFEST - call set_app_manifest with:
   - App name and description
   - List of screens with descriptions
   - Tab structure (if app uses tabs)
   - This is CRITICAL - downstream agents need this to navigate and validate

3. CREATE TASKS for each capture based on YOUR expert judgment:
   - Which screens show the app's value?
   - Which animations/interactions are impressive?
   - How many assets does this video need?

4. FINALIZE with analysis summary

IMPORTANT: The app_manifest you create will be passed to:
- Capturer (knows how to navigate to each screen)
- Validator (knows what each screen should look like)

Without a good manifest, captures will fail because agents won't know the app structure.

Start by exploring the project structure.""",
    )
    
    agent.invoke({
        "messages": [HumanMessage(content=f"Analyze {state['project_path']} and create capture tasks.")]
    })
    
    # Create video project with full context
    video_project_id = None
    if _ctx.analysis_summary:
        video_project_id = create_video_project(
            user_input=state["user_input"],
            project_path=state["project_path"],
            app_bundle_id=app_bundle_id,
            analysis_summary=_ctx.analysis_summary
        )
        # Track in session
        session.video_project_id = video_project_id
        
        print(f"✓ Analysis complete: {_ctx.tasks_created} tasks, project {video_project_id[:8]}...")
        if _ctx.app_manifest:
            print(f"  App: {_ctx.app_manifest.get('app_name', 'Unknown')}")
            print(f"  Screens: {len(_ctx.app_manifest.get('screens', []))}")
    else:
        print(f"⚠️  Analysis complete but no summary finalized")
    
    return {
        "video_project_id": video_project_id,
        "app_manifest": _ctx.app_manifest,
        "messages": [AIMessage(content="Analysis complete.")]
    }
