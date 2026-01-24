"""
Editor Composers - Version-specific composer implementations.

Set EDITOR_VERSION env var to switch versions (default: v2)
"""
import os

VERSION = os.getenv("EDITOR_VERSION", "v2")

if VERSION == "v1":
    from .v1 import compose_all_clips_node
    compose_single_clip_node = None  # V1 doesn't have parallel
else:  # v2 is default
    from .v2 import compose_all_clips_node, compose_single_clip_node

__all__ = ["compose_all_clips_node", "compose_single_clip_node", "VERSION"]
