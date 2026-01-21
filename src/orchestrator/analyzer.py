"""
Analyzer node: Domain expert. OWNS all video production decisions.

- Reads user_input directly to understand intent
- Explores codebase to understand the app
- Forms expert opinion on what to capture
- Creates tasks based on ITS judgment
- Writes comprehensive analysis for downstream phases
- Creates video_project record with full context
"""
from typing import Optional

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

from config import get_model
from tools import ANALYZER_TOOLS
from db.supabase_client import create_task, create_video_project
from .state import PipelineState
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

_ctx = AnalyzerContext()


def reset_context():
    global _ctx
    _ctx = AnalyzerContext()


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────

def create_tools(app_bundle_id: str):
    """Create tools for the analyzer agent."""
    
    @tool
    def create_capture_task(description: str, capture_type: str) -> str:
        """
        Create a capture task in the database.
        
        Args:
            description: Full description - what to capture, how to navigate,
                        what makes a good capture. Be detailed.
            capture_type: "screenshot" or "recording"
        
        Returns:
            Confirmation with task ID
        """
        ctype = "recording" if "record" in capture_type.lower() else "screenshot"
        task_id = create_task(
            app_bundle_id=app_bundle_id,
            task_description=description,
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
        
        Call this AFTER creating all capture tasks. This summary will guide
        the editor in the next phase, so include:
        - Your understanding of what the user wants
        - Why you chose these specific captures
        - How they should fit together (pacing, flow, story)
        - Any important notes for editing
        
        Args:
            analysis_summary: Your complete analysis and strategy
        
        Returns:
            Confirmation
        """
        _ctx.analysis_summary = analysis_summary
        return f"Analysis finalized. {_ctx.tasks_created} tasks created."
    
    return [create_capture_task, finalize_analysis]


# ─────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────

def analyze_and_plan_node(state: PipelineState) -> dict:
    """Analyzer node: explores codebase, creates tasks, writes analysis."""
    reset_context()
    print(f"\n🔍 Analyzing project...")
    
    # Update session state
    session = get_session()
    session.current_stage = "analyzing"
    
    app_bundle_id = state.get("app_bundle_id", "com.app.unknown")
    session.app_bundle_id = app_bundle_id
    
    tools = ANALYZER_TOOLS + create_tools(app_bundle_id)
    
    agent = create_react_agent(
        model=get_model(),
        tools=tools,
        name="analyzer",
        prompt=f"""You are an expert iOS developer AND video producer.

USER'S REQUEST:
{state['user_input']}

PROJECT PATH: {state['project_path']}

YOUR TOOLS:
- list_directory, read_file, run_bash: Explore the codebase
- create_capture_task: Create a task for something worth capturing
- finalize_analysis: Write your complete strategy (call this LAST)

YOUR JOB:
1. EXPLORE the codebase - understand the app's structure and features
2. UNDERSTAND what the user wants for their video (duration, vibe, purpose)
3. DECIDE what to capture based on YOUR expert judgment:
   - Which screens show the app's value?
   - Which animations/interactions are impressive?
   - How many assets does this video actually need?
   - What mix of screenshots vs recordings?
4. CREATE TASKS for each thing worth capturing
5. FINALIZE with a comprehensive analysis that includes:
   - Your understanding of the user's goals
   - Why you chose these captures
   - How they should flow together
   - Pacing/timing suggestions
   - Any notes for the editor

You are THE expert here. Don't wait for instructions on asset count or timing - 
that's YOUR call based on the app and user's request.

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
    else:
        print(f"⚠️  Analysis complete but no summary finalized")
    
    return {
        "video_project_id": video_project_id,
        "messages": [AIMessage(content="Analysis complete.")]
    }
