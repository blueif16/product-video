"""
Editor Phase - Video composition, music generation, and assembly.

Transforms captured assets into a VideoSpec for Remotion rendering,
with aligned background music.

## Layer-Based Architecture (Simplified)

Each clip is a self-contained "moment" with multiple layers:
- Background layers (solid colors, gradients, animated orbs)
- Image layers (captured screenshots/recordings OR AI-generated images)
- Text layers (typography, callouts)

NOTE: There's no separate "GeneratedImageLayer" - all images use ImageLayer.
Generated images are just images with a src path. The model knows what it
generated (it wrote the prompt). Simpler code, fewer special cases.

## Music Generation

After assembly, the music phase:
1. Analyzes the clip timeline for hit points and energy levels
2. Groups clips into musical sections
3. Generates an ElevenLabs composition plan
4. Creates BGM that aligns with visual beats

## Standalone Usage

```python
from editor import run_editor_standalone

# Load project from DB and run full editor pipeline (with music)
result = run_editor_standalone("video-project-uuid")

# Skip music generation
result = run_editor_standalone("video-project-uuid", include_music=False)

# Skip rendering (just create VideoSpec + music)
result = run_editor_standalone("video-project-uuid", include_render=False)

# Run just the music phase
result = run_music_only("video-project-uuid")
```

## Testing

```python
from editor import create_test_state, build_editor_graph

# Create mock state for testing
state = create_test_state(
    user_input="30s energetic promo",
    assets=[{"id": "1", "path": "/path/to/asset.png", ...}]
)

# Text-only test (no assets)
state = create_test_state(text_only=True)

# Build graph without render/music
graph = build_editor_graph(include_render=False, include_music=False)
```

## Pipeline Flow

```
EditorState (from loader or capture phase)
    ↓
planner (creates clip_tasks with creative notes)
    ↓
compose_clips (builds layer-based specs)
    ↓
assembler (collects specs → VideoSpec JSON)
    ↓
music_plan (analyzes timeline → composition plan)
    ↓
music_generate (ElevenLabs → aligned BGM)
    ↓
render (optional: Remotion CLI)
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
from .state import (
    EditorState,
    ClipSpec,
    VideoSpec,
    AudioSpec,
    # Layer types (simplified - no GeneratedImageLayer)
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
from .music_planner import (
    analyze_timeline_for_music,
    extract_hit_points,
    HitPoint,
    MusicSection,
    EnergyLevel,
)

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
    
    # Layer types (simplified)
    "Layer",
    "BackgroundLayer",
    "ImageLayer",
    # NOTE: GeneratedImageLayer removed - use ImageLayer for all images
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
]
