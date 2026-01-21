"""
Intake node: Traffic cop. Validates project path and extracts bundle ID.
Knows NOTHING about video production - that's the analyzer's job.
"""
from typing import Optional
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt, Command
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

from config import get_model
from tools.xcode_tools import extract_project_info
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
        self.url_schemes: list[str] = []
        self.project_name: Optional[str] = None
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
def validate_xcode_project(project_path: str) -> str:
    """
    Validate an Xcode project and extract bundle ID programmatically.
    
    This REPLACES guessing - it reads the actual project files to get
    the real bundle ID, URL schemes, and project name.
    
    Args:
        project_path: Path to .xcodeproj or directory containing it
    
    Returns:
        Project info including bundle_id, or error message
    """
    expanded = str(Path(project_path).expanduser())
    
    if not Path(expanded).exists():
        return f"ERROR: Path does not exist: {expanded}"
    
    # Extract project info programmatically
    info = extract_project_info(expanded)
    
    if info["error"] and not info["bundle_id"]:
        return f"ERROR: {info['error']}"
    
    # Store in context
    _ctx.project_path = info["xcodeproj_path"] or expanded
    _ctx.app_bundle_id = info["bundle_id"]
    _ctx.url_schemes = info["url_schemes"]
    _ctx.project_name = info["project_name"]
    _ctx.ready_to_proceed = True
    
    # Build result message
    result = f"✓ Project validated: {_ctx.project_name}\n"
    result += f"  Bundle ID: {_ctx.app_bundle_id}\n"
    if _ctx.url_schemes:
        result += f"  URL schemes: {', '.join(_ctx.url_schemes)}\n"
    result += f"  Path: {_ctx.project_path}"
    
    return result


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


TOOLS = [check_path_exists, validate_xcode_project, request_user_input]


# ─────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────

def intake_node(state: PipelineState) -> Command:
    """Intake node: validates project path and extracts bundle ID."""
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
        prompt=f"""You are a simple intake validator. Your ONLY job is to validate the Xcode project.

USER REQUEST:
{state['user_input']}

CURRENT INFO:
{info_str}

YOUR TOOLS:
1. check_path_exists(path) - Verify a path exists (optional, for debugging)
2. validate_xcode_project(path) - MAIN TOOL: validates project and extracts real bundle ID
3. request_user_input(question) - Ask user if project path is missing/invalid

YOUR JOB:
1. Find the Xcode project path in the user's request
2. Call validate_xcode_project(path) - it extracts the REAL bundle ID from project files
3. If no path found or validation fails, call request_user_input

DO NOT guess the bundle ID - validate_xcode_project reads it from project.pbxproj.

CRITICAL: Call validate_xcode_project if you have a path, OR request_user_input if you don't.""",
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
        print(f"  Bundle ID: {_ctx.app_bundle_id}")
        if _ctx.url_schemes:
            print(f"  URL schemes: {_ctx.url_schemes}")
        
        # Update session with bundle ID
        session.app_bundle_id = _ctx.app_bundle_id
        
        return Command(
            update={
                "project_path": _ctx.project_path,
                "app_bundle_id": _ctx.app_bundle_id,
                "url_schemes": _ctx.url_schemes,  # Pass to analyzer via state
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
