"""
Tool exports for capture agents.

Note: Editor tools (create_clip_task, submit_clip_spec, etc.) are imported
directly in the editor module, not exported here.
"""
from .bash_tools import run_bash, read_file, write_file, list_directory

from .capture_tools import (
    # Environment setup
    set_status_bar,
    clear_status_bar,
    set_appearance,
    grant_permission,
    
    # App navigation
    launch_app,
    terminate_app,
    open_url,
    
    # UI interaction
    tap,
    double_tap,
    long_press,
    swipe,
    type_text,
    press_key,
    press_home,
    
    # Capture
    capture_screenshot,
    capture_recording,
    start_recording,
    stop_recording,
    
    # Utilities
    wait_seconds,
    get_simulator_info,
    describe_screen,
    get_interaction_status,
    
    # Backend detection (not a tool, but useful)
    INTERACTION_BACKEND,
)

from .validation_tool import validate_capture, get_recording_action_log, verify_screen

# Editor tools (for reference, import directly from editor_tools.py)
from .editor_tools import (
    # Planner tools
    create_clip_task,
    finalize_edit_plan,
    
    # Composer tools
    submit_clip_spec,
    generate_enhanced_image,
    
    # Helper functions (not tools)
    get_pending_clip_tasks,
    get_composed_clip_specs,
    get_generated_assets,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL SETS FOR DIFFERENT AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

# Tools for the Analyzer Agent (reads codebase, doesn't interact with simulator)
ANALYZER_TOOLS = [
    run_bash,
    read_file,
    list_directory,
]

# Full tool set for the Capturer Agent
CAPTURER_TOOLS = [
    # Bash/File (for debugging, checking files)
    run_bash,
    read_file,
    write_file,
    
    # Environment setup (call once at session start)
    set_status_bar,
    clear_status_bar,
    set_appearance,
    grant_permission,
    
    # Navigation
    launch_app,
    terminate_app,
    open_url,
    
    # Interaction
    tap,
    double_tap,
    long_press,
    swipe,
    type_text,
    press_key,
    press_home,
    
    # Capture
    capture_screenshot,
    capture_recording,
    start_recording,
    stop_recording,
    
    # Utilities
    wait_seconds,
    get_simulator_info,
    describe_screen,
    get_interaction_status,
    
    # Validation & Verification
    validate_capture,
    verify_screen,  # NEW: Check screen before capture
    get_recording_action_log,
]

# Minimal tool set for quick screenshots only
SCREENSHOT_TOOLS = [
    set_status_bar,
    set_appearance,
    launch_app,
    open_url,
    tap,
    swipe,
    wait_seconds,
    capture_screenshot,
    validate_capture,
    verify_screen,
    get_simulator_info,
]

# Tool set for recordings with interactions
RECORDING_TOOLS = [
    set_status_bar,
    set_appearance,
    grant_permission,
    launch_app,
    open_url,
    tap,
    double_tap,
    long_press,
    swipe,
    type_text,
    press_key,
    wait_seconds,
    start_recording,
    stop_recording,
    validate_capture,
    verify_screen,
    get_recording_action_log,
    get_simulator_info,
]

# ═══════════════════════════════════════════════════════════════════════════════
# EDITOR TOOL SETS
# ═══════════════════════════════════════════════════════════════════════════════

# Tools for the Edit Planner (creates clip_tasks)
PLANNER_TOOLS = [
    create_clip_task,
    finalize_edit_plan,
]

# Tools for the Clip Composer (creates layer specs, can generate images)
COMPOSER_TOOLS = [
    submit_clip_spec,
    generate_enhanced_image,
]
