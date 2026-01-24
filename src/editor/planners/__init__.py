"""
Editor Planners - Version-specific planner implementations.

Set EDITOR_VERSION env var to switch versions (default: v2)
"""
import os

VERSION = os.getenv("EDITOR_VERSION", "v2")

if VERSION == "v1":
    from .v1 import edit_planner_node
else:  # v2 is default
    from .v2 import edit_planner_node

__all__ = ["edit_planner_node", "VERSION"]
