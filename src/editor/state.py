"""
Editor Phase State Definitions

The editor phase transforms captured assets into a VideoSpec for Remotion.
State flows: loader → planner → composers → assembler → renderer

## Key Concept: Layer-Based Clips

A clip_task represents a "moment" in the video, not just a single asset.
Each clip can have multiple layers:
- Image layers (original screenshots/recordings)
- Generated image layers (AI-enhanced visuals)
- Text layers (typography, callouts)

This allows the composer to create rich, self-contained moments
without coordinating separate text tracks.
"""
from typing import Annotated, Optional, Literal
from typing_extensions import TypedDict
import operator


# ─────────────────────────────────────────────────────────────
# Layer Types
# ─────────────────────────────────────────────────────────────

class TransformSpec(TypedDict, total=False):
    """Transform animation for a layer."""
    type: Literal["static", "ken_burns", "zoom_in", "zoom_out", "pan"]
    startScale: float
    endScale: float
    startX: float
    endX: float
    startY: float
    endY: float
    easing: Literal["spring", "ease_out", "ease_in_out", "linear"]


class OpacitySpec(TypedDict, total=False):
    """Opacity animation for a layer."""
    start: float  # 0-1
    end: float    # 0-1
    easing: Literal["linear", "ease_out", "ease_in_out"]


class ImageLayer(TypedDict, total=False):
    """A layer containing an image/video asset."""
    type: Literal["image"]
    src: str                    # Path to asset
    zIndex: int                 # Stack order (higher = on top)
    transform: TransformSpec
    opacity: OpacitySpec
    startFrame: int             # Relative to clip start (default 0)
    durationFrames: int         # Duration within clip (default: full clip)
    deviceFrame: Optional[dict] # {type, shadow}


class GeneratedImageLayer(TypedDict, total=False):
    """A layer containing an AI-generated image."""
    type: Literal["generated_image"]
    src: str                    # Path to generated asset
    generatedAssetId: str       # Reference to generated_assets table
    prompt: str                 # What was generated
    zIndex: int
    transform: TransformSpec
    opacity: OpacitySpec
    startFrame: int
    durationFrames: int


class TextStyleSpec(TypedDict, total=False):
    """Typography styling."""
    fontSize: int           # Pixels
    fontWeight: int         # 400, 500, 600, 700, 800
    fontFamily: str         # "Inter", "SF Pro", etc.
    color: str              # Hex color
    textAlign: Literal["left", "center", "right"]
    lineHeight: float       # Multiplier
    letterSpacing: float    # Pixels


class TextAnimationSpec(TypedDict, total=False):
    """Text animation parameters."""
    enter: Literal["fade", "slide_up", "slide_down", "slide_left", "slide_right", "scale", "typewriter"]
    exit: Literal["fade", "slide_up", "slide_down", "slide_left", "slide_right", "scale", "none"]
    enterDurationFrames: int
    exitDurationFrames: int
    stagger: bool           # For typewriter/character effects
    staggerDelay: int       # Frames between characters


class TextPositionSpec(TypedDict, total=False):
    """Text positioning."""
    preset: Literal["center", "top", "bottom", "top-left", "top-right", "bottom-left", "bottom-right"]
    x: float                # Custom X (% of frame, overrides preset)
    y: float                # Custom Y (% of frame, overrides preset)
    maxWidth: float         # % of frame width


class TextLayer(TypedDict, total=False):
    """A layer containing text/typography."""
    type: Literal["text"]
    content: str            # The text to display
    zIndex: int
    style: TextStyleSpec
    animation: TextAnimationSpec
    position: TextPositionSpec
    startFrame: int         # Relative to clip start
    durationFrames: int
    opacity: OpacitySpec


# Union type for all layers
Layer = ImageLayer | GeneratedImageLayer | TextLayer


# ─────────────────────────────────────────────────────────────
# Clip Spec (Layer-Based)
# ─────────────────────────────────────────────────────────────

class TransitionSpec(TypedDict, total=False):
    """Transition between clips."""
    type: Literal["fade", "slide", "wipe", "zoom", "none"]
    durationFrames: int
    direction: Literal["left", "right", "up", "down"]  # For slide/wipe


class ClipSpec(TypedDict, total=False):
    """
    Technical specification for a single clip/moment.
    
    A clip is a self-contained "moment" in the video that can have
    multiple visual layers (images, generated images, text).
    
    This is what Remotion needs to render.
    """
    id: str
    startFrame: int              # Position in timeline
    durationFrames: int          # Total duration
    
    # The core: multiple layers composited together
    layers: list[Layer]
    
    # Transitions between clips
    enterTransition: Optional[TransitionSpec]
    exitTransition: Optional[TransitionSpec]
    
    # Composer's reasoning (for debugging/iteration)
    composerNotes: str


# ─────────────────────────────────────────────────────────────
# Video Spec (Final Output)
# ─────────────────────────────────────────────────────────────

class VideoSpec(TypedDict, total=False):
    """
    Complete video specification for Remotion.
    This is the contract between Python and TypeScript.
    """
    meta: dict  # {title, durationFrames, fps, resolution}
    clips: list[ClipSpec]
    audio: Optional[dict]  # {src, volume, beatTimestamps} - added in music phase


# ─────────────────────────────────────────────────────────────
# Editor State
# ─────────────────────────────────────────────────────────────

class EditorState(TypedDict):
    """
    State for the editor phase.
    
    Can be:
    - Loaded from DB (standalone mode)
    - Passed from capture phase (full pipeline mode)
    - Created manually (test mode)
    """
    # ─────────────────────────────────────────────────────────
    # Identity
    # ─────────────────────────────────────────────────────────
    video_project_id: str
    
    # ─────────────────────────────────────────────────────────
    # Context from capture phase (flows through unchanged)
    # ─────────────────────────────────────────────────────────
    user_input: str
    analysis_summary: str
    
    # ─────────────────────────────────────────────────────────
    # Assets to work with
    # ─────────────────────────────────────────────────────────
    assets: list[dict]  # [{id, path, description, capture_type, validation_notes}]
    
    # ─────────────────────────────────────────────────────────
    # Planner outputs
    # ─────────────────────────────────────────────────────────
    edit_plan_summary: Optional[str]      # Planner's overall vision
    clip_task_ids: list[str]              # IDs of created clip_tasks
    
    # ─────────────────────────────────────────────────────────
    # Composer outputs (accumulated from processing)
    # ─────────────────────────────────────────────────────────
    clip_specs: Annotated[list[ClipSpec], operator.add]
    generated_asset_ids: Annotated[list[str], operator.add]  # Track generated assets
    
    # Track composition progress
    pending_clip_task_ids: Optional[list[str]]
    current_clip_index: Optional[int]
    
    # ─────────────────────────────────────────────────────────
    # Assembler outputs
    # ─────────────────────────────────────────────────────────
    video_spec: Optional[VideoSpec]
    video_spec_id: Optional[str]  # DB ID
    
    # ─────────────────────────────────────────────────────────
    # Renderer outputs
    # ─────────────────────────────────────────────────────────
    render_status: Optional[str]  # 'pending' | 'rendering' | 'complete' | 'failed'
    render_path: Optional[str]
    render_error: Optional[str]


# ─────────────────────────────────────────────────────────────
# Clip Composer State (for individual task processing)
# ─────────────────────────────────────────────────────────────

class ClipComposerState(TypedDict):
    """State for individual clip composition."""
    task_id: str
    asset_path: str
    start_time_s: float
    duration_s: float
    composer_notes: str
    video_project_id: str
    
    # Context for LLM to understand the creative vision
    user_input: str
    analysis_summary: str
    
    # Available assets for reference
    all_assets: list[dict]
