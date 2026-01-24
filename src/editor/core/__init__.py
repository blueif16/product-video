"""
Editor Core - Shared components that don't change between versions.
"""

from .state import (
    EditorState,
    ClipSpec,
    VideoSpec,
    AudioSpec,
    Layer,
    BackgroundLayer,
    ImageLayer,
    TextLayer,
    TransformSpec,
    OpacitySpec,
    TextStyleSpec,
    TextAnimationSpec,
    TextPositionSpec,
    TransitionSpec,
)
from .loader import load_editor_state, create_test_state, load_or_create_state
from .assembler import edit_assembler_node, assemble_video_spec
from .music_planner import (
    music_planner_node,
    analyze_timeline_for_music,
    extract_hit_points,
    HitPoint,
    MusicSection,
    EnergyLevel,
)

__all__ = [
    # State
    "EditorState",
    "ClipSpec",
    "VideoSpec", 
    "AudioSpec",
    "Layer",
    "BackgroundLayer",
    "ImageLayer",
    "TextLayer",
    "TransformSpec",
    "OpacitySpec",
    "TextStyleSpec",
    "TextAnimationSpec",
    "TextPositionSpec",
    "TransitionSpec",
    # Loader
    "load_editor_state",
    "create_test_state",
    "load_or_create_state",
    # Assembler
    "edit_assembler_node",
    "assemble_video_spec",
    # Music
    "music_planner_node",
    "analyze_timeline_for_music",
    "extract_hit_points",
    "HitPoint",
    "MusicSection",
    "EnergyLevel",
]
