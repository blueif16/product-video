"""
Pipeline Module

Combined flows for running multiple phases together.

## Full Pipeline (Capture → Editor → Render)

```python
from pipeline import run_full_pipeline

result = run_full_pipeline(
    user_input="30s energetic promo for my FocusFlow app at ~/Code/FocusFlow",
    include_render=True,
)

if result.get("render_path"):
    print(f"Video at: {result['render_path']}")
```

## Build Custom Pipeline

```python
from pipeline import build_full_pipeline

graph = build_full_pipeline(include_render=False)
# Use graph.invoke() with custom state
```
"""

from .full_graph import (
    build_full_pipeline,
    run_full_pipeline,
    FullPipelineState,
    capture_to_editor_bridge,
)

__all__ = [
    "build_full_pipeline",
    "run_full_pipeline",
    "FullPipelineState",
    "capture_to_editor_bridge",
]
