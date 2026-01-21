"""
DEPRECATED: Text Composer

This file is kept for reference but is no longer used in the pipeline.
Text overlays are now handled as layers within the clip_composer.

The layer-based architecture (implemented in clip_composer.py) allows
each clip to have multiple layers including text, eliminating the need
for a separate text composition step.

See clip_composer.py for how text layers are now handled.
"""

# This module is intentionally empty.
# The functionality has been merged into clip_composer.py.

def _deprecated_warning():
    import warnings
    warnings.warn(
        "text_composer is deprecated. Text layers are now part of clip_composer.",
        DeprecationWarning,
        stacklevel=2
    )

# If anyone imports from this module, warn them
_deprecated_warning()
