"""
Editor Phase State Definitions

The editor phase transforms captured assets into a VideoSpec for Remotion.
State flows: loader → planner → composers → assembler → renderer

## Key Concept: Layer-Based Clips

A clip_task represents a "moment" in the video, not just a single asset.
Each clip can have multiple layers:
- Background layers (solid colors, gradients, animated orbs, grid, noise)
- Image layers (original screenshots/recordings OR AI-generated images)
- Text layers (typography, callouts, counters)

## Animation Philosophy

Every animation has a "feel" controlled by spring physics:
- snappy: Fast, no bounce (corporate, professional)
- smooth: Medium speed, gentle ease (elegant, premium)
- bouncy: Overshoot and settle (playful, energetic)

## Simplification: Unified Image Type

All image assets (captured or generated) use the same ImageLayer type.
The description field carries semantic info like dimensions.
"""
from typing import Annotated, Optional, Literal, Union
from typing_extensions import TypedDict
import operator


# ─────────────────────────────────────────────────────────────
# Animation Feel (Spring Physics Presets)
# ─────────────────────────────────────────────────────────────

# These map to spring config in Remotion:
# snappy:  { damping: 25, stiffness: 400, mass: 0.3 }
# smooth:  { damping: 20, stiffness: 150, mass: 0.5 }
# bouncy:  { damping: 8, stiffness: 200, mass: 0.5 }
AnimationFeel = Literal["snappy", "smooth", "bouncy"]


# ─────────────────────────────────────────────────────────────
# Transform Types
# ─────────────────────────────────────────────────────────────

class TransformSpec(TypedDict, total=False):
    """Transform animation for image layers."""
    type: Literal[
        "static",       # No movement
        "ken_burns",    # Classic documentary zoom
        "zoom_in",      # Slow zoom towards center
        "zoom_out",     # Slow zoom away from center
        "pan_left",     # Drift left
        "pan_right",    # Drift right
        "pan_up",       # Drift up
        "pan_down",     # Drift down
        "focus",        # Zoom towards specific point
        "parallax",     # Depth-based scrolling effect
    ]
    startScale: float       # Starting scale (default 1.0)
    endScale: float         # Ending scale (default varies by type)
    focusX: float           # For focus type - percentage from left (0-100)
    focusY: float           # For focus type - percentage from top (0-100)
    intensity: float        # 0.5 = subtle, 1.0 = normal, 1.5 = dramatic
    parallaxSpeed: float    # For parallax type - 0.5 = half speed, 2 = double
    parallaxDirection: Literal["horizontal", "vertical"]


class OpacitySpec(TypedDict, total=False):
    """Opacity animation for a layer."""
    start: float  # 0-1
    end: float    # 0-1


# ─────────────────────────────────────────────────────────────
# Background Layer Types
# ─────────────────────────────────────────────────────────────

class GradientSpec(TypedDict, total=False):
    """Gradient specification for backgrounds."""
    colors: list[str]  # List of hex colors
    angle: int         # Degrees (0-360)
    animate: bool      # Subtle angle animation


class BackgroundLayer(TypedDict, total=False):
    """
    A layer containing a background (for text-only clips or under images).
    
    Types:
    - Solid color: Just set color
    - Gradient: Set gradient with colors and angle
    - Orbs: Animated glowing spheres (premium SaaS vibe)
    - Grid: Subtle technical grid pattern
    - Noise: Film grain texture (editorial feel)
    - Radial: Centered radial gradient (spotlight effect)
    """
    type: Literal["background"]
    zIndex: int                    # Usually 0 (bottom)
    
    # Solid color
    color: str                     # Hex color (e.g., "#0f172a")
    
    # Gradient
    gradient: GradientSpec
    
    # Animated orbs (mutually exclusive with gradient)
    orbs: bool                     # Enable floating orbs
    orbColors: list[str]           # Custom orb colors (default: primary, accent, accentAlt)
    
    # Grid pattern
    grid: bool                     # Enable grid overlay
    gridSize: int                  # Grid cell size in pixels (default 40)
    gridColor: str                 # Grid line color
    gridAnimated: bool             # Animate grid movement
    
    # Noise texture
    noise: bool                    # Enable noise overlay
    noiseOpacity: float            # 0-1 (default 0.05)
    
    # Radial gradient
    radial: bool                   # Enable radial gradient
    radialCenterX: int             # Center X percentage (default 50)
    radialCenterY: int             # Center Y percentage (default 50)
    radialCenterColor: str         # Center color
    radialEdgeColor: str           # Edge color


# ─────────────────────────────────────────────────────────────
# Image Layer
# ─────────────────────────────────────────────────────────────

class ImageLayer(TypedDict, total=False):
    """
    A layer containing an image/video asset.
    
    Supports:
    - Captured screenshots/recordings
    - AI-generated images
    - Device frames (iPhone, MacBook, iPad)
    - Ken Burns transforms
    - Opacity animations for crossfades
    """
    type: Literal["image"]
    src: str                    # Path to asset
    zIndex: int                 # Stack order (higher = on top)
    transform: TransformSpec    # Movement/zoom animation
    opacity: OpacitySpec        # For crossfade effects
    startFrame: int             # Relative to clip start (default 0)
    durationFrames: int         # Duration within clip (default: full clip)
    device: Literal["none", "iphone", "iphonePro", "macbook", "ipad"]


# ─────────────────────────────────────────────────────────────
# Text Layer - Full Animation Support
# ─────────────────────────────────────────────────────────────

class TextStyleSpec(TypedDict, total=False):
    """Typography styling."""
    fontSize: int           # Pixels (24-32 caption, 36-48 callout, 56-72 headline, 80-160 hero)
    fontWeight: int         # 400 regular, 500 medium, 600 semibold, 700 bold, 800 extrabold, 900 black
    color: str              # Hex color (e.g., "#FFFFFF")
    textAlign: Literal["left", "center", "right"]
    lineHeight: float       # Multiplier (default 1.2)
    letterSpacing: str      # CSS value (e.g., "-0.02em", "-0.03em" for tight hero text)
    textShadow: str         # CSS text-shadow (e.g., "0 4px 30px rgba(0,0,0,0.5)")
    maxWidth: int           # Max width in pixels (for wrapping)
    
    # Highlight-specific styling
    highlightColor: str     # Color for highlight animation (underline or background)


class TextAnimationSpec(TypedDict, total=False):
    """
    Text animation parameters.
    
    Enter animations:
    - fade: Simple opacity fade in
    - scale: Scale from 0.85 to 1 (punchy)
    - pop: Scale with bounce overshoot (playful)
    - slide_up/down/left/right: Slide from direction
    - typewriter: Characters appear one by one
    - stagger: Words animate in sequence with spring
    - reveal: Mask reveal from direction
    - glitch: Distortion effect then settle
    - highlight: Animated underline or background
    - countup: Animate number from 0 to value
    - none: No animation
    
    Exit animations:
    - fade: Opacity fade out
    - slide_up/down: Slide out
    - scale: Scale down and fade
    - none: Cut (no animation)
    """
    enter: Literal[
        "fade",
        "scale",
        "pop",           # Bouncy scale with overshoot
        "slide_up",
        "slide_down",
        "slide_left",
        "slide_right",
        "typewriter",
        "stagger",       # Words animate in sequence
        "reveal",        # Mask reveal
        "glitch",        # Distortion effect
        "highlight",     # Animated underline/background
        "countup",       # Number counting animation
        "none"
    ]
    exit: Literal[
        "fade",
        "slide_up",
        "slide_down",
        "scale",
        "none"
    ]
    enterDuration: int      # Custom enter duration in frames (default ~8)
    exitDuration: int       # Custom exit duration in frames (default ~6)
    feel: AnimationFeel     # snappy | smooth | bouncy (controls spring physics)
    
    # Typewriter-specific
    typewriterSpeed: int    # Frames per character (default 2)
    showCursor: bool        # Show blinking cursor
    
    # Stagger-specific
    staggerBy: Literal["word", "character"]  # What to stagger
    staggerDelay: int       # Frames between items (default 3)
    
    # Reveal-specific
    revealDirection: Literal["left", "right", "top", "bottom"]
    
    # Highlight-specific
    highlightType: Literal["underline", "background"]
    
    # Countup-specific (content should be the target number)
    countupFrom: int        # Starting number (default 0)
    countupDecimals: int    # Decimal places (default 0)
    countupPrefix: str      # e.g., "$"
    countupSuffix: str      # e.g., "M+"
    
    # Glitch-specific
    glitchIntensity: float  # 0.5 = subtle, 1.0 = normal, 2.0 = intense


class TextPositionSpec(TypedDict, total=False):
    """Text positioning."""
    preset: Literal[
        "center",
        "top",
        "bottom",
        "left",
        "right",
        "top_left",
        "top_right",
        "bottom_left",
        "bottom_right"
    ]
    x: float    # Custom X position (% from left, 50 = center)
    y: float    # Custom Y position (% from top, 50 = center)


class TextLayer(TypedDict, total=False):
    """A layer containing text/typography."""
    type: Literal["text"]
    content: str            # The text to display (or target number for countup)
    zIndex: int
    style: TextStyleSpec
    animation: TextAnimationSpec
    position: TextPositionSpec
    startFrame: int         # Relative to clip start (default 0)
    durationFrames: int     # How long text is visible


# ─────────────────────────────────────────────────────────────
# Layer Union Type
# ─────────────────────────────────────────────────────────────

Layer = Union[BackgroundLayer, ImageLayer, TextLayer]


# ─────────────────────────────────────────────────────────────
# Clip Spec (Layer-Based)
# ─────────────────────────────────────────────────────────────

class TransitionSpec(TypedDict, total=False):
    """Transition between clips."""
    type: Literal[
        "fade",
        "slide",        # Default slide (left)
        "slide_left",
        "slide_right",
        "slide_up",
        "slide_down",
        "wipe",
        "none"
    ]
    durationFrames: int


class ClipSpec(TypedDict, total=False):
    """
    Technical specification for a single clip/moment.
    
    A clip is a self-contained "moment" in the video that can have
    multiple visual layers (backgrounds, images, text).
    """
    id: str
    startFrame: int              # Position in timeline
    durationFrames: int          # Total duration
    
    # The core: multiple layers composited together
    layers: list[Layer]
    
    # Transitions between clips
    enterTransition: Optional[TransitionSpec]
    exitTransition: Optional[TransitionSpec]
    
    # Background color fallback (used if no background layer)
    backgroundColor: Optional[str]
    
    # Composer's reasoning (for debugging/iteration)
    composerNotes: str


# ─────────────────────────────────────────────────────────────
# Video Spec (Final Output)
# ─────────────────────────────────────────────────────────────

class AudioSpec(TypedDict, total=False):
    """Audio track specification."""
    src: str                 # Path to audio file
    volume: float            # 0-1 (default 0.5)
    startFrame: int          # When audio starts (default 0)
    fadeIn: int              # Fade in duration in frames (default 30)
    fadeOut: int             # Fade out duration in frames (default 30)
    loop: bool               # Loop audio


class MetaSpec(TypedDict):
    """Video metadata."""
    title: str
    durationFrames: int
    fps: int
    resolution: dict  # {width: int, height: int}


class VideoSpec(TypedDict, total=False):
    """
    Complete video specification for Remotion.
    This is the contract between Python and TypeScript.
    """
    meta: MetaSpec
    clips: list[ClipSpec]
    audio: Optional[AudioSpec]
    backgroundColor: Optional[str]  # Global background color


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
    # Identity
    video_project_id: str
    
    # Context from capture phase
    user_input: str
    analysis_summary: str
    
    # Assets to work with (description includes dimensions)
    assets: list[dict]  # [{id, path, description}]
    
    # Planner outputs
    edit_plan_summary: Optional[str]
    clip_task_ids: list[str]
    
    # Composer outputs
    clip_specs: Annotated[list[ClipSpec], operator.add]
    generated_asset_ids: Annotated[list[str], operator.add]
    
    # Composition progress tracking
    pending_clip_task_ids: Optional[list[str]]
    current_clip_index: Optional[int]
    
    # Assembler outputs
    video_spec: Optional[VideoSpec]
    video_spec_id: Optional[str]
    
    # Music generation outputs
    music_analysis: Optional[dict]      # Timeline analysis for music
    composition_plan: Optional[dict]    # ElevenLabs composition plan
    refined_composition_plan: Optional[dict]  # LLM-refined plan
    audio_path: Optional[str]           # Generated BGM file path
    
    # Renderer outputs
    render_status: Optional[str]  # 'pending' | 'rendering' | 'complete' | 'failed'
    render_path: Optional[str]
    render_error: Optional[str]
    
    # Final outputs (video + audio muxed)
    final_video_path: Optional[str]  # Video with muxed audio
    mux_error: Optional[str]


# ─────────────────────────────────────────────────────────────
# Clip Composer State
# ─────────────────────────────────────────────────────────────

class ClipComposerState(TypedDict):
    """State for individual clip composition."""
    task_id: str
    asset_path: str
    start_time_s: float
    duration_s: float
    composer_notes: str
    video_project_id: str
    
    # Context for creative vision
    user_input: str
    analysis_summary: str
    
    # Available assets for reference
    all_assets: list[dict]
