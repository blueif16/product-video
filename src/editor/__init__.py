"""
Editor Phase - Video composition and assembly.

## Structure

- core/: Shared components (assembler, loader, state, music_planner)
- planners/: Version-specific planners (v1, v2)
- composers/: Version-specific composers (v1, v2)
- graph.py: Main orchestration graph

## Version Selection

Set EDITOR_VERSION env var to switch versions:
- v1: Original planner/composer
- v2: Sequential timeline + cognitive load (default)

## Usage

```python
from editor import run_editor_standalone

# Run full pipeline
result = run_editor_standalone("video-project-uuid")

# Partial runs
from editor import run_assembly_only, run_music_only
run_assembly_only("video-project-uuid")
```
"""

from .graph import (
    build_editor_graph,
    run_editor_standalone,
    run_editor_test,
    run_editor_with_checkpointer,
    run_composing_only,
    run_assembly_only,
    run_music_only,
)

from .core.state import (
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

from .core.loader import load_editor_state, create_test_state, load_or_create_state

from .core.music_planner import (
    analyze_timeline_for_music,
    extract_hit_points,
    HitPoint,
    MusicSection,
    EnergyLevel,
)

from .planners import VERSION as PLANNER_VERSION
from .composers import VERSION as COMPOSER_VERSION

__all__ = [
    # Graph builders & runners
    "build_editor_graph",
    "run_editor_standalone",
    "run_editor_test",
    "run_editor_with_checkpointer",
    "run_composing_only",
    "run_assembly_only",
    "run_music_only",
    
    # State types
    "EditorState",
    "ClipSpec",
    "VideoSpec",
    "AudioSpec",
    
    # Layer types
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
    
    # Loaders
    "load_editor_state",
    "create_test_state",
    "load_or_create_state",
    
    # Music planning
    "analyze_timeline_for_music",
    "extract_hit_points",
    "HitPoint",
    "MusicSection",
    "EnergyLevel",
    
    # Versions
    "PLANNER_VERSION",
    "COMPOSER_VERSION",
]
