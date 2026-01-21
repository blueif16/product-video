"""
Intake node: Traffic cop. Validates project path, nothing else.
Knows NOTHING about video production - that's the analyzer's job.
"""
from typing import Optional
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt, Command
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

from config import get_model
from .state import PipelineState
from .session import get_session


# ─────────────────────────────────────────────────────────────
# Context
# ─────────────────────────────────────────────────────────────

class IntakeContext:
    """Minimal context for intake tools."""
    def __init__(self):
        self.project_path: Optional[str] = None
        self.app_bundle_id: Optional[str] = None
        self.ready_to_proceed: bool = False
        self.needs_user_input: bool = False
        self.user_question: Optional[str] = None

_ctx = IntakeContext()


def reset_context():
    global _ctx
    _ctx = IntakeContext()


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────

@tool
def check_path_exists(path: str) -> str:
    """
    Check if a file path exists on the system.
    
    Args:
        path: Path to check (can include ~)
    
    Returns:
        Whether path exists and its expanded form
    """
    expanded = str(Path(path).expanduser())
    exists = Path(expanded).exists()
    if exists:
        return f"Path EXISTS: {expanded}"
    else:
        return f"Path DOES NOT EXIST: {expanded}"


@tool
def confirm_project(project_path: str, app_bundle_id: str) -> str:
    """
    Confirm the project is valid and proceed to analysis.
    
    Args:
        project_path: Full path to Xcode project (expand ~ first)
        app_bundle_id: Bundle ID like com.company.appname (infer from project name)
    
    Returns:
        Confirmation message
    """
    expanded = str(Path(project_path).expanduser())
    
    if not Path(expanded).exists():
        return f"ERROR: Path does not exist: {expanded}. Ask the user for the correct path."
    
    _ctx.project_path = expanded
    _ctx.app_bundle_id = app_bundle_id
    _ctx.ready_to_proceed = True
    
    return f"Project confirmed: {expanded}. Ready for analysis."


@tool
def request_user_input(question: str) -> str:
    """
    Request information from the user (typically the project path).
    
    Args:
        question: The question to ask
    
    Returns:
        Confirmation that input was requested
    """
    _ctx.needs_user_input = True
    _ctx.user_question = question
    return f"User input requested: {question}"


TOOLS = [check_path_exists, confirm_project, request_user_input]


# ─────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────

def intake_node(state: PipelineState) -> Command:
    """Intake node: validates project path only."""
    reset_context()
    
    # Update session stage
    session = get_session()
    session.current_stage = "intake"
    
    # Build minimal context
    current_info = []
    if state.get("project_path"):
        current_info.append(f"Project path: {state['project_path']}")
    info_str = "\n".join(current_info) if current_info else "(none)"
    
    agent = create_react_agent(
        model=get_model(),
        tools=TOOLS,
        name="intake",
        prompt=f"""You are a simple intake validator. Your ONLY job is to confirm we have a valid Xcode project path.

USER REQUEST:
{state['user_input']}

CURRENT INFO:
{info_str}

YOUR TOOLS:
1. check_path_exists(path) - Verify a path exists
2. confirm_project(path, bundle_id) - Confirm and proceed (call when path is valid)
3. request_user_input(question) - Ask user for the project path if missing

YOUR JOB:
1. Find the Xcode project path in the user's request
2. If found, verify it exists with check_path_exists
3. If valid, call confirm_project with the path and an inferred bundle_id
4. If no path found or invalid, call request_user_input

You don't need to understand video requirements - just validate the path.
Infer bundle_id from project name (e.g., MyApp.xcodeproj → com.app.myapp)

CRITICAL: Call either confirm_project OR request_user_input.""",
    )
    
    agent.invoke({
        "messages": [HumanMessage(content=f"Validate project path from: {state['user_input']}")]
    })
    
    if _ctx.needs_user_input:
        answer = interrupt({
            "question": _ctx.user_question,
            "hint": "Example: ~/Code/MyApp/MyApp.xcodeproj"
        })
        new_input = f"{state['user_input']}\n\nProject path: {answer}"
        return Command(
            update={
                "user_input": new_input,
                "messages": [AIMessage(content=f"User provided: {answer}")]
            },
            goto="intake"
        )
    
    if _ctx.ready_to_proceed:
        print(f"✓ Intake complete: {_ctx.project_path}")
        
        # Update session with bundle ID
        session.app_bundle_id = _ctx.app_bundle_id
        
        return Command(
            update={
                "project_path": _ctx.project_path,
                "app_bundle_id": _ctx.app_bundle_id,
                "intake_complete": True,
                "messages": [AIMessage(content="Intake complete.")]
            },
            goto="analyze_and_plan"
        )
    
    # Fallback
    answer = interrupt({
        "question": "I need the path to your Xcode project.",
        "hint": "Example: ~/Code/MyApp/MyApp.xcodeproj"
    })
    new_input = f"{state['user_input']}\n\nProject path: {answer}"
    return Command(
        update={"user_input": new_input, "messages": [AIMessage(content=f"User provided: {answer}")]},
        goto="intake"
    )
