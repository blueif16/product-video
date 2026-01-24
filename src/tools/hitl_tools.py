"""
Human-in-the-Loop (HITL) tools for capture agent.

When the agent gets stuck exploring (can't find target screen), 
these tools allow it to ask a human for guidance.
"""
from langchain_core.tools import tool
from dataclasses import dataclass, field
from typing import Optional, List
import sys


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLORATION STATE TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass  
class ExplorationState:
    """
    Track exploration attempts to detect when agent is stuck.
    
    Reset this at the start of each capture task.
    """
    # Counts
    describe_calls: int = 0
    navigation_attempts: int = 0  # taps, swipes, open_urls
    
    # History for human context
    screens_seen: List[str] = field(default_factory=list)  # Brief descriptions
    actions_taken: List[str] = field(default_factory=list)  # Action log
    
    # Target info
    target_description: str = ""
    
    # HITL state
    human_guidance_received: Optional[str] = None
    hitl_requested: bool = False
    
    def record_describe(self, brief_description: str = ""):
        """Record a describe_screen call."""
        self.describe_calls += 1
        if brief_description:
            # Keep last 5 unique screens
            if brief_description not in self.screens_seen[-5:]:
                self.screens_seen.append(brief_description)
            if len(self.screens_seen) > 10:
                self.screens_seen = self.screens_seen[-10:]
    
    def record_navigation(self, action: str):
        """Record a navigation action (tap, swipe, open_url)."""
        self.navigation_attempts += 1
        self.actions_taken.append(action)
        # Keep last 15 actions
        if len(self.actions_taken) > 15:
            self.actions_taken = self.actions_taken[-15:]
    
    def is_stuck(self, max_describe: int, max_nav: int) -> bool:
        """Check if exploration limits exceeded."""
        return (
            self.describe_calls >= max_describe or 
            self.navigation_attempts >= max_nav
        )
    
    def get_context_for_human(self) -> str:
        """Generate context string to show human."""
        lines = []
        lines.append(f"🎯 Target: {self.target_description}")
        lines.append(f"📊 Stats: {self.describe_calls} describe calls, {self.navigation_attempts} navigation attempts")
        
        if self.screens_seen:
            lines.append(f"\n📱 Screens seen (last {len(self.screens_seen)}):")
            for i, screen in enumerate(self.screens_seen[-5:], 1):
                # Truncate long descriptions
                if len(screen) > 100:
                    screen = screen[:97] + "..."
                lines.append(f"  {i}. {screen}")
        
        if self.actions_taken:
            lines.append(f"\n🔄 Recent actions (last {min(10, len(self.actions_taken))}):")
            for action in self.actions_taken[-10:]:
                lines.append(f"  • {action}")
        
        return "\n".join(lines)


# Global exploration state (reset per task)
_exploration_state = ExplorationState()


def reset_exploration_state(target_description: str = ""):
    """Reset exploration state for a new capture task."""
    global _exploration_state
    _exploration_state = ExplorationState(target_description=target_description)


def get_exploration_state() -> ExplorationState:
    """Get current exploration state."""
    return _exploration_state


# ═══════════════════════════════════════════════════════════════════════════════
# HITL TOOL
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def request_human_guidance(
    situation: str,
    what_i_tried: str,
    specific_question: str
) -> str:
    """
    🆘 ASK A HUMAN FOR HELP when you're stuck and can't find the target screen.
    
    Use this when:
    - You've tried multiple navigation paths and none work
    - The screen you see doesn't match what you expected
    - You can't figure out how to reach the target from current state
    - Deep links don't work and you don't know the UI path
    
    The human will see your situation and can provide:
    - Specific coordinates to tap
    - A working deep link
    - Step-by-step navigation instructions
    - Information that the target doesn't exist / is inaccessible
    
    Args:
        situation: Describe what screen you're currently on
        what_i_tried: Brief summary of navigation attempts that didn't work
        specific_question: Clear question for the human (be specific!)
    
    Returns:
        Human's guidance (coordinates, deep link, instructions, or "skip")
    
    Example:
        request_human_guidance(
            situation="I'm on the main dashboard with tabs: Home, Chat, Profile",
            what_i_tried="Tried open_url(yiban://inventory), tapped all tabs, swiped through screens",
            specific_question="How do I access the Inventory/Closet screen? Is there a specific tab or menu?"
        )
    """
    from config import Config
    
    # Mark that HITL was requested
    _exploration_state.hitl_requested = True
    
    # Build context for human
    print("\n" + "=" * 70)
    print("🆘 AGENT REQUESTING HUMAN GUIDANCE")
    print("=" * 70)
    
    # Show exploration context
    print("\n" + _exploration_state.get_context_for_human())
    
    print("\n" + "-" * 70)
    print(f"📍 Current situation: {situation}")
    print(f"\n🔄 What I tried: {what_i_tried}")
    print(f"\n❓ Question: {specific_question}")
    print("-" * 70)
    
    # Check if HITL is enabled
    if not Config.ENABLE_HITL:
        print("\n⚠️  HITL disabled (ENABLE_HITL=false). Returning 'skip' to fail gracefully.")
        return "SKIP: HITL disabled, cannot complete this task."
    
    # Interactive prompt
    print("\n📝 Enter your guidance (or commands):")
    print("   • Type coordinates like: tap 200 400")
    print("   • Type a deep link like: open yiban://closet")
    print("   • Type navigation steps")
    print("   • Type 'skip' to skip this task")
    print("   • Type 'abort' to stop the entire pipeline")
    print("")
    
    try:
        guidance = input("Your guidance: ").strip()
    except EOFError:
        # Non-interactive mode
        return "SKIP: Non-interactive environment, cannot get human input."
    except KeyboardInterrupt:
        print("\n⏸️  Interrupted by user")
        return "ABORT: User interrupted"
    
    if not guidance:
        return "SKIP: No guidance provided"
    
    # Store guidance
    _exploration_state.human_guidance_received = guidance
    
    # Handle special commands
    if guidance.lower() == "skip":
        return "SKIP: Human chose to skip this task."
    
    if guidance.lower() == "abort":
        return "ABORT: Human chose to abort the pipeline."
    
    print(f"\n✅ Got guidance: {guidance}")
    print("=" * 70 + "\n")
    
    return f"HUMAN GUIDANCE: {guidance}"


@tool
def report_exploration_stuck() -> str:
    """
    Report that you're stuck exploring and need help.
    
    This is a lighter-weight version of request_human_guidance that 
    automatically generates the context from your exploration history.
    
    Use this when you've exceeded exploration limits and the prompt
    is telling you to ask for help.
    
    Returns:
        Either human guidance, or instructions to skip/fail the task
    """
    from config import Config
    
    state = _exploration_state
    
    # Build automatic summary
    situation = f"After {state.describe_calls} screen descriptions and {state.navigation_attempts} navigation attempts"
    
    what_tried = "Multiple taps, swipes, and navigation attempts"
    if state.actions_taken:
        what_tried = ", ".join(state.actions_taken[-5:])
    
    question = f"How do I reach: {state.target_description}?"
    
    # Delegate to the full HITL tool
    return request_human_guidance.invoke({
        "situation": situation,
        "what_i_tried": what_tried, 
        "specific_question": question
    })


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLORATION CHECK TOOL (for agent to self-check)
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def check_exploration_budget() -> str:
    """
    Check how many exploration attempts you have left.
    
    Returns:
        Status string with remaining budget and whether you should ask for help.
    """
    from config import Config
    
    state = _exploration_state
    
    describe_remaining = Config.MAX_DESCRIBE_CALLS - state.describe_calls
    nav_remaining = Config.MAX_NAVIGATION_ATTEMPTS - state.navigation_attempts
    
    if state.is_stuck(Config.MAX_DESCRIBE_CALLS, Config.MAX_NAVIGATION_ATTEMPTS):
        return (
            f"⚠️ EXPLORATION LIMIT REACHED! "
            f"({state.describe_calls}/{Config.MAX_DESCRIBE_CALLS} describes, "
            f"{state.navigation_attempts}/{Config.MAX_NAVIGATION_ATTEMPTS} nav attempts). "
            f"You MUST call request_human_guidance or report_capture_result(success=False)."
        )
    
    status = "OK"
    if describe_remaining <= 3 or nav_remaining <= 5:
        status = "LOW"
    
    return (
        f"Budget {status}: "
        f"{describe_remaining} describes left, "
        f"{nav_remaining} navigation attempts left. "
        f"{'Consider asking for help soon.' if status == 'LOW' else ''}"
    )
