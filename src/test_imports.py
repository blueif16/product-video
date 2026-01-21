#!/usr/bin/env python3
"""
Quick import test to verify all modules load correctly.
Run from the src directory: python test_imports.py
"""

import sys
from pathlib import Path

# Add src to path if running directly
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def test_imports():
    """Test all imports work correctly."""
    print("Testing imports...")
    
    # Test config
    print("  ✓ config", end="")
    from config import Config, get_model
    print(f" (model: {Config.MODEL_NAME})")
    
    # Test tools
    print("  ✓ tools/__init__", end="")
    from tools import (
        CAPTURER_TOOLS, 
        ANALYZER_TOOLS, 
        INTERACTION_BACKEND,
        capture_screenshot,
        start_recording,
        stop_recording,
        tap,
        swipe,
        set_status_bar,
        open_url,
        validate_capture,
    )
    print(f" ({len(CAPTURER_TOOLS)} capturer tools, backend: {INTERACTION_BACKEND})")
    
    # Test capture_tools directly
    print("  ✓ tools/capture_tools")
    from tools.capture_tools import (
        set_status_bar,
        clear_status_bar,
        set_appearance,
        grant_permission,
        launch_app,
        terminate_app,
        open_url,
        tap,
        double_tap,
        long_press,
        swipe,
        type_text,
        press_key,
        press_home,
        capture_screenshot,
        capture_recording,
        start_recording,
        stop_recording,
        wait_seconds,
        get_simulator_info,
        describe_screen,
        get_interaction_status,
    )
    
    # Test validation_tool
    print("  ✓ tools/validation_tool")
    from tools.validation_tool import validate_capture, get_recording_action_log
    
    # Test bash_tools
    print("  ✓ tools/bash_tools")
    from tools.bash_tools import run_bash, read_file, write_file, list_directory
    
    # Test agents
    print("  ✓ agents/capturer_agent")
    from agents.capturer_agent import create_capturer_agent
    
    print("  ✓ agents/analyzer_agent")
    from agents.analyzer_agent import create_analyzer_agent
    
    print("\n" + "=" * 50)
    print("All imports successful!")
    print("=" * 50)
    
    # Print tool summary
    print(f"\nCAPTURER_TOOLS ({len(CAPTURER_TOOLS)} tools):")
    for tool in CAPTURER_TOOLS:
        print(f"  - {tool.name}")
    
    print(f"\nInteraction backend: {INTERACTION_BACKEND}")


if __name__ == "__main__":
    test_imports()
