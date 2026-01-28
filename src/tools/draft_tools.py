"""
Clip Spec Draft Tools

Token-efficient tools for building clip specs through a validate-edit loop.
The model drafts → validates → edits → validates → submits.

This avoids repeating large JSON in context by using file-based drafting.

Tools:
- draft_clip_spec: Write initial layers to draft file
- edit_draft_spec: Apply targeted edits to draft
- validate_clip_spec: Compute bounding boxes, check constraints
"""
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, List, Optional
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

DRAFT_DIR = Path("/tmp/clip_drafts")
REMOTION_DIR = Path(__file__).parent.parent.parent / "remotion"
MEASURE_SCRIPT = REMOTION_DIR / "scripts" / "measure-layers.js"

# Canvas constants (must match measure-layers.js)
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080
SAFE_ZONE = {
    "left": 230,    # 12% of 1920
    "right": 1690,  # 88% of 1920
    "top": 130,     # 12% of 1080
    "bottom": 950,  # 88% of 1080
}


# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────

def get_draft_path(clip_id: str) -> Path:
    """Get deterministic draft file path for a clip."""
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    return DRAFT_DIR / f"{clip_id}.json"


def read_draft(clip_id: str) -> Optional[List[dict]]:
    """Read draft layers from file."""
    path = get_draft_path(clip_id)
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return json.load(f)


def write_draft(clip_id: str, layers: List[dict]) -> Path:
    """Write layers to draft file."""
    path = get_draft_path(clip_id)
    with open(path, 'w') as f:
        json.dump(layers, f, indent=2)
    return path


def run_measure_script(layers: List[dict]) -> dict:
    """Run Node.js measurement script and return results."""
    # Write layers to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(layers, f)
        temp_path = f.name
    
    try:
        # Run node script
        result = subprocess.run(
            ['node', str(MEASURE_SCRIPT), temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REMOTION_DIR),
        )
        
        if result.returncode != 0:
            return {
                "error": f"Measurement script failed: {result.stderr}",
                "fallback": True,
            }
        
        return json.loads(result.stdout)
        
    except subprocess.TimeoutExpired:
        return {"error": "Measurement script timed out", "fallback": True}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON from measurement: {e}", "fallback": True}
    except FileNotFoundError:
        return {"error": "Node.js not found - using fallback estimation", "fallback": True}
    finally:
        Path(temp_path).unlink(missing_ok=True)


def estimate_text_bbox(layer: dict) -> dict:
    """Fallback text bounding box estimation (pure Python)."""
    content = layer.get('content', '')
    style = layer.get('style', {})
    position = layer.get('position', {})
    
    font_size = style.get('fontSize', 48)
    line_height = style.get('lineHeight', 1.2)
    max_width = style.get('maxWidth')
    
    # Estimate text dimensions
    char_width_ratio = 0.55
    text_width = len(content) * font_size * char_width_ratio
    text_height = font_size * line_height
    
    # Handle maxWidth wrapping
    if max_width and text_width > max_width:
        line_count = int(text_width / max_width) + 1
        text_width = min(text_width, max_width)
        text_height = text_height * line_count
    
    # Calculate position
    anchor = position.get('anchor', 'center')
    
    if position.get('preset'):
        preset = position['preset'].replace('-', '_')
        if preset == 'center':
            x, y = CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2
        elif preset == 'top':
            x, y = CANVAS_WIDTH / 2, SAFE_ZONE['top'] + text_height / 2
        elif preset == 'bottom':
            x, y = CANVAS_WIDTH / 2, SAFE_ZONE['bottom'] - text_height / 2
        else:
            x, y = CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2
    else:
        x = (position.get('x', 50) / 100) * CANVAS_WIDTH
        y = (position.get('y', 50) / 100) * CANVAS_HEIGHT
    
    # Calculate bounds based on anchor
    if anchor == 'center':
        left = x - text_width / 2
        top = y - text_height / 2
    elif anchor == 'top-left':
        left, top = x, y
    elif anchor == 'top-right':
        left = x - text_width
        top = y
    elif anchor == 'bottom-left':
        left = x
        top = y - text_height
    elif anchor == 'bottom-right':
        left = x - text_width
        top = y - text_height
    else:
        left = x - text_width / 2
        top = y - text_height / 2
    
    return {
        'width': int(text_width),
        'height': int(text_height),
        'left': int(left),
        'top': int(top),
        'right': int(left + text_width),
        'bottom': int(top + text_height),
    }


def fallback_validate(layers: List[dict]) -> dict:
    """Fallback validation using Python estimation."""
    results = {
        'canvas': {'width': CANVAS_WIDTH, 'height': CANVAS_HEIGHT},
        'safeZone': SAFE_ZONE,
        'layers': [],
        'issues': [],
    }
    
    for i, layer in enumerate(layers):
        layer_type = layer.get('type', 'unknown')
        
        if layer_type == 'background':
            results['layers'].append({
                'index': i,
                'type': 'background',
                'status': 'OK',
            })
            continue
        
        if layer_type == 'text':
            bbox = estimate_text_bbox(layer)
            issues = []
            
            # Check safe zone
            if bbox['left'] < SAFE_ZONE['left']:
                issues.append({'type': 'bleed_left', 'value': bbox['left']})
            if bbox['right'] > SAFE_ZONE['right']:
                issues.append({'type': 'bleed_right', 'value': bbox['right']})
            if bbox['top'] < SAFE_ZONE['top']:
                issues.append({'type': 'bleed_top', 'value': bbox['top']})
            if bbox['bottom'] > SAFE_ZONE['bottom']:
                issues.append({'type': 'bleed_bottom', 'value': bbox['bottom']})
            
            results['layers'].append({
                'index': i,
                'type': 'text',
                'content': layer.get('content', '')[:30],
                'fontSize': layer.get('style', {}).get('fontSize'),
                'bbox': bbox,
                'status': 'BLEED' if issues else 'OK',
                'issues': issues if issues else None,
            })
            continue
        
        # Other layer types - basic pass
        results['layers'].append({
            'index': i,
            'type': layer_type,
            'status': 'OK',
        })
    
    return results


def format_validation_report(results: dict) -> str:
    """Format measurement results into concise report."""
    lines = ["LAYERS:"]
    
    for layer in results.get('layers', []):
        idx = layer['index']
        ltype = layer['type']
        status = layer.get('status', 'OK')
        
        if ltype == 'background':
            subtype = layer.get('subtype', 'solid')
            lines.append(f"  {idx}: background ({subtype}) - {status}")
            continue
        
        if ltype == 'text':
            content = layer.get('content', '')
            font_size = layer.get('fontSize', '?')
            bbox = layer.get('bbox', {})
            
            w, h = bbox.get('width', '?'), bbox.get('height', '?')
            left, right = bbox.get('left', '?'), bbox.get('right', '?')
            top, bottom = bbox.get('top', '?'), bbox.get('bottom', '?')
            
            lines.append(
                f"  {idx}: text '{content}' {font_size}px → {w}×{h}px "
                f"at ({left},{top})-({right},{bottom}) - {status}"
            )
            continue
        
        if ltype in ('image', 'generated_image'):
            device = layer.get('device', 'none')
            scale = layer.get('scale', 1.0)
            bbox = layer.get('bbox', {})
            
            w, h = bbox.get('width', '?'), bbox.get('height', '?')
            left, right = bbox.get('left', '?'), bbox.get('right', '?')
            top, bottom = bbox.get('top', '?'), bbox.get('bottom', '?')
            
            device_str = f" device:{device}" if device != 'none' else ""
            scale_str = f" scale:{scale}" if scale != 1.0 else ""
            
            lines.append(
                f"  {idx}: image{device_str}{scale_str} → {w}×{h}px "
                f"at ({left},{top})-({right},{bottom}) - {status}"
            )
            continue
        
        lines.append(f"  {idx}: {ltype} - {status}")
    
    # Issues
    all_issues = []
    
    # Layer-specific issues
    for layer in results.get('layers', []):
        if layer.get('issues'):
            for issue in layer['issues']:
                issue_type = issue.get('type', 'unknown')
                if issue_type.startswith('bleed_'):
                    direction = issue_type.replace('bleed_', '')
                    value = issue.get('value', '?')
                    limit = SAFE_ZONE.get(direction, '?')
                    all_issues.append(
                        f"⚠️ Layer {layer['index']} {direction} edge {value}px "
                        f"exceeds safe zone {limit}px"
                    )
    
    # Global issues (overlaps, spacing)
    for issue in results.get('issues', []):
        issue_type = issue.get('type', 'unknown')
        
        if issue_type == 'overlap':
            a, b = issue.get('layerA', '?'), issue.get('layerB', '?')
            w = issue.get('overlapWidth', '?')
            h = issue.get('overlapHeight', '?')
            all_issues.append(f"❌ OVERLAP: Layer {a} and {b} overlap by {w}×{h}px")
        
        elif issue_type == 'tight_spacing':
            a, b = issue.get('layerA', '?'), issue.get('layerB', '?')
            gap = issue.get('gap', '?')
            min_gap = issue.get('minGap', '?')
            all_issues.append(
                f"⚠️ TIGHT: Layer {a} and {b} have {gap}px gap (need {min_gap}px)"
            )
    
    if all_issues:
        lines.append("\nISSUES:")
        lines.extend(f"  {issue}" for issue in all_issues)
    else:
        lines.append("\n✓ All checks passed")
    
    return "\n".join(lines)


def set_nested_value(obj: dict, path: str, value) -> None:
    """Set a value in a nested dict using dot notation path."""
    keys = path.split('.')
    for key in keys[:-1]:
        if key not in obj:
            obj[key] = {}
        obj = obj[key]
    obj[keys[-1]] = value


def validate_timing(layers: List[dict], clip_duration: int) -> List[str]:
    """Check for timing errors (layers that won't render correctly)."""
    issues = []

    for i, layer in enumerate(layers):
        if layer.get('type') == 'background':
            continue

        start = layer.get('startFrame', 0)
        enter_dur = layer.get('animation', {}).get('enterDuration', 0)
        animation_end = start + enter_dur

        content = layer.get('content', layer.get('src', layer.get('type', '')))[:25]

        # Layer starts after clip ends - will never appear
        if start >= clip_duration:
            issues.append(f"❌ Layer {i} '{content}' starts at {start}, clip ends at {clip_duration}")

        # Animation completes after clip ends - will be cut off
        elif animation_end > clip_duration:
            issues.append(f"❌ Layer {i} '{content}' animation ends at {animation_end}, clip ends at {clip_duration}")

    return issues


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────

@tool
def draft_clip_spec(
    layers_json: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """
    Write layers array to draft file for validation and editing.

    Args:
        layers_json: JSON array of layer specifications

    Returns:
        Confirmation message

    Example:
        layers_json = '''[
            {"type": "background", "zIndex": 0, "color": "#0f172a"},
            {"type": "text", "content": "HERO", "zIndex": 2,
             "position": {"x": 50, "y": 45, "anchor": "center"},
             "style": {"fontSize": 120, "fontWeight": 800}}
        ]'''
    """
    clip_id = state.get("clip_id")
    if not clip_id:
        return "ERROR: No clip_id in state"

    # Parse layers
    try:
        layers = json.loads(layers_json)
        if not isinstance(layers, list):
            return "ERROR: layers_json must be a JSON array"
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON: {e}"

    # Write draft
    path = write_draft(clip_id, layers)

    print(f"   📝 Draft saved: {len(layers)} layers → {path.name}")

    return f"Draft saved with {len(layers)} layers. Call validate_clip_spec to check layout."


@tool
def edit_draft_spec(
    edits: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """
    Apply targeted edits to draft spec without rewriting entire spec.

    Args:
        edits: JSON array of edit operations:
            [{"layer_index": 2, "field_path": "position.y", "value": 60}]

    Returns:
        Confirmation of applied edits

    Examples:
        edits = '[{"layer_index": 2, "field_path": "position.y", "value": 60}]'
        edits = '[{"layer_index": 2, "field_path": "style.fontSize", "value": 80}]'
    """
    clip_id = state.get("clip_id")
    if not clip_id:
        return "ERROR: No clip_id in state"
    
    # Read current draft
    layers = read_draft(clip_id)
    if layers is None:
        return "ERROR: No draft found. Call draft_clip_spec first."
    
    # Parse edits
    try:
        edit_list = json.loads(edits)
        if not isinstance(edit_list, list):
            return "ERROR: edits must be a JSON array"
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON in edits: {e}"
    
    # Apply edits
    applied = 0
    for edit in edit_list:
        idx = edit.get('layer_index')
        path = edit.get('field_path')
        value = edit.get('value')
        
        if idx is None or path is None or value is None:
            continue
        
        if idx < 0 or idx >= len(layers):
            continue
        
        set_nested_value(layers[idx], path, value)
        applied += 1
    
    # Save updated draft
    write_draft(clip_id, layers)
    
    print(f"   ✏️  Applied {applied} edit(s)")
    
    return f"Applied {applied} edit(s). Call validate_clip_spec to verify."


@tool
def validate_clip_spec(
    state: Annotated[dict, InjectedState],
) -> str:
    """
    Compute bounding boxes and check for safe zone violations, overlaps, spacing issues, and timing.

    Returns:
        Validation report with layer dimensions and issues (if any)

    Safe Zone: x:230-1690, y:130-950 (12% margins on 1920×1080 canvas)
    """
    clip_id = state.get("clip_id")
    if not clip_id:
        return "ERROR: No clip_id in state"

    # Read draft
    layers = read_draft(clip_id)
    if layers is None:
        return "ERROR: No draft found. Call draft_clip_spec first."

    clip_duration = state.get("duration_frames", 150)  # From state

    # Spatial validation (existing)
    results = run_measure_script(layers)

    if results.get('fallback') or results.get('error'):
        print(f"   ⚠️  Using fallback validation: {results.get('error', 'unknown')}")
        results = fallback_validate(layers)

    # Format spatial report
    report = format_validation_report(results)

    # Timing validation
    timing_issues = validate_timing(layers, clip_duration)
    if timing_issues:
        report += "\n\nTIMING:\n  " + "\n  ".join(timing_issues)
    else:
        report += "\n\n✓ Timing OK"

    # Check if passed
    has_errors = any(
        layer.get('status') in ('BLEED', 'ERROR')
        for layer in results.get('layers', [])
    )
    has_overlaps = any(
        issue.get('type') == 'overlap'
        for issue in results.get('issues', [])
    )
    has_timing_errors = any('❌' in issue for issue in timing_issues)

    if has_errors or has_overlaps or has_timing_errors:
        print(f"   ⚠️  Validation found issues")
    else:
        print(f"   ✓ Validation passed")

    print(f"\n{report}\n")

    return report
