"""
Editor Phase - Video composition and assembly.

Transforms captured assets into a VideoSpec for Remotion rendering.

## Layer-Based Architecture

Each clip is a self-contained "moment" with multiple layers:
- Image layers (original screenshots/recordings)
- Generated image layers (AI-enhanced visuals)
- Text layers (typography, callouts)

Text overlays are no longer separate tasks - they're layers within clips.

## Standalone Usage

```python
from editor import run_editor_standalone

# Load project from DB and run full editor pipeline
result = run_editor_standalone("video-project-uuid")

# Skip rendering (just create VideoSpec)
result = run_editor_standalone("video-project-uuid", include_render=False)
```

## Testing

```python
from editor import create_test_state, build_editor_graph

# Create mock state for testing
state = create_test_state(
    user_input="30s energetic promo",
    assets=[{"id": "1", "path": "/path/to/asset.png", ...}]
)

# Build graph without render step
graph = build_editor_graph(include_render=False)
```

## As Subgraph

```python
from editor import build_editor_graph

# Use as a node in a larger graph
editor_graph = build_editor_graph()
parent_builder.add_node("editor_phase", editor_graph)
```

## Pipeline Flow

```
EditorState (from loader or capture phase)
    ↓
planner (creates clip_tasks in DB with rich creative notes)
    ↓
compose_clips (for each task: interprets notes → layer-based spec)
    - Can generate AI-enhanced images
    - Can add text layers
    - Can create multi-layer transitions
    ↓
assembler (collects specs → VideoSpec JSON)
    ↓
render (optional: calls Remotion CLI)
```
"""

from .graph import (
    build_editor_graph,
    run_editor_standalone,
    run_editor_test,
    run_editor_with_checkpointer,
)
from .state import (
    EditorState,
    ClipSpec,
    VideoSpec,
    # Layer types
    Layer,
    ImageLayer,
    GeneratedImageLayer,
    TextLayer,
    TransformSpec,
    OpacitySpec,
    TextStyleSpec,
    TextAnimationSpec,
    TextPositionSpec,
    TransitionSpec,
)
from .loader import load_editor_state, create_test_state, load_or_create_state

__all__ = [
    # Graph builders & runners
    "build_editor_graph",
    "run_editor_standalone",
    "run_editor_test",
    "run_editor_with_checkpointer",
    
    # State types
    "EditorState",
    "ClipSpec",
    "VideoSpec",
    
    # Layer types
    "Layer",
    "ImageLayer",
    "GeneratedImageLayer",
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
]
