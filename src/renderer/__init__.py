"""
Renderer Module

Python interface for calling Remotion to render videos.

## Usage

```python
from renderer import render_video, check_remotion_available

# Check if Remotion is set up
available, msg = check_remotion_available()

# Render a video
success, output_path, error = render_video(
    video_spec=spec,
    output_filename="promo.mp4",
)
```
"""

from .render_client import (
    render_video,
    render_still,
    check_remotion_available,
    remotion_render_node,
    REMOTION_PROJECT_PATH,
    RENDERS_DIR,
    SPECS_DIR,
)

__all__ = [
    "render_video",
    "render_still",
    "check_remotion_available",
    "remotion_render_node",
    "REMOTION_PROJECT_PATH",
    "RENDERS_DIR",
    "SPECS_DIR",
]
