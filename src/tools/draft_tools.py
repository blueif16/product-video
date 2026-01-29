"""
Clip Spec Draft Tools — Real Pixel Validation

Token-efficient tools for building clip specs through a validate-edit loop.
The model drafts → validates → edits → validates → submits.

Tools:
- draft_clip_spec: Write initial layers to draft file
- edit_draft_spec: Apply targeted edits to draft
- validate_clip_spec: Compute bounding boxes, check constraints (REAL measurements)
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
MEASURE_SCRIPT = REMOTION_DIR / "scripts" / "measure-real.ts"

CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080
SAFE_ZONE = {
    "left": 230,
    "right": 1690,
    "top": 130,
    "bottom": 950,
}

MIN_SPACING = 40  # Minimum px between elements


# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────

def get_draft_path(clip_id: str) -> Path:
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    return DRAFT_DIR / f"{clip_id}.json"


def read_draft(clip_id: str) -> Optional[List[dict]]:
    path = get_draft_path(clip_id)
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return json.load(f)


def write_draft(clip_id: str, layers: List[dict]) -> Path:
    path = get_draft_path(clip_id)
    with open(path, 'w') as f:
        json.dump(layers, f, indent=2)
    return path


def run_measure_script(layers: List[dict]) -> dict:
    """Run TypeScript measurement script and return results."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(layers, f)
        temp_path = f.name
    
    try:
        result = subprocess.run(
            ['npx', 'tsx', str(MEASURE_SCRIPT), temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REMOTION_DIR),
        )
        
        if result.returncode != 0:
            return {"error": f"Measure failed: {result.stderr}", "fallback": True}
        
        return json.loads(result.stdout)
        
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "fallback": True}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "fallback": True}
    except FileNotFoundError:
        return {"error": "npx/tsx not found", "fallback": True}
    finally:
        Path(temp_path).unlink(missing_ok=True)


def set_nested_value(obj: dict, path: str, value) -> None:
    """Set value in nested dict using dot notation."""
    import re
    parts = re.split(r'\.|\[', path)
    parts = [p.rstrip(']') for p in parts if p]
    
    current = obj
    for i, key in enumerate(parts[:-1]):
        if key.isdigit():
            current = current[int(key)]
        else:
            if key not in current:
                next_key = parts[i + 1] if i + 1 < len(parts) else None
                current[key] = [] if next_key and next_key.isdigit() else {}
            current = current[key]
    
    final_key = parts[-1]
    if final_key.isdigit():
        current[int(final_key)] = value
    else:
        current[final_key] = value


def validate_timing(layers: List[dict], clip_duration: int) -> List[str]:
    """Check for timing errors."""
    issues = []
    for i, layer in enumerate(layers):
        if layer.get('type') == 'background':
            continue
        start = layer.get('startFrame', 0)
        enter_dur = layer.get('animation', {}).get('enterDuration', 0)
        if start >= clip_duration:
            issues.append(f"❌ [{i}] starts at {start}, clip ends at {clip_duration}")
        elif start + enter_dur > clip_duration:
            issues.append(f"❌ [{i}] animation ends at {start + enter_dur}, clip ends at {clip_duration}")
    return issues


def format_concise_report(results: dict, layers: List[dict], clip_duration: int) -> str:
    """Format validation results into concise, scannable report."""
    lines = []
    
    # ─────────────────────────────────────────────────────────
    # LAYOUT section - one line per layer
    # ─────────────────────────────────────────────────────────
    lines.append("LAYOUT:")
    for info in results.get('layers', []):
        idx = info['index']
        ltype = info['type']
        bbox = info.get('bbox')
        
        if ltype == 'background':
            lines.append(f"  [{idx}] background")
            continue
        
        if not bbox:
            lines.append(f"  [{idx}] {ltype}")
            continue
        
        size = f"{bbox['width']}×{bbox['height']}"
        pos = f"({bbox['centerX']}, {bbox['centerY']})"
        
        extra = ""
        if ltype == 'text':
            content = info.get('content', '')[:20]
            fs = info.get('fontSize', '?')
            lc = info.get('lineCount', 1)
            wrap = f" ⚠️{lc}lines" if lc > 1 else ""
            extra = f" '{content}' {fs}px{wrap}"
        
        lines.append(f"  [{idx}] {ltype:8} {size:>10} @ {pos:>15}{extra}")
    
    # ─────────────────────────────────────────────────────────
    # SPACING section - gaps between elements
    # ─────────────────────────────────────────────────────────
    spacing = results.get('spacing', [])
    if spacing:
        lines.append("")
        lines.append("SPACING:")
        for sp in spacing:
            a, b = sp['a'], sp['b']
            gap = sp['gap']
            
            if gap < 0:
                status = f"❌ OVERLAP"
            elif gap < MIN_SPACING:
                status = f"⚠️ min {MIN_SPACING}px"
            else:
                status = "✓"
            
            lines.append(f"  [{a}]↔[{b}]: {gap:>4}px  {status}")
    
    # ─────────────────────────────────────────────────────────
    # CONTRAST section
    # ─────────────────────────────────────────────────────────
    contrast = results.get('contrast', [])
    if contrast:
        lines.append("")
        lines.append("CONTRAST:")
        for c in contrast:
            idx = c['layerIndex']
            ratio = c['ratio']
            readable = c['readable']
            
            if readable:
                lines.append(f"  [{idx}]: {ratio:.1f} ✓")
            else:
                bg = c['bgSamples'][0] if c['bgSamples'] else '?'
                tc = c['textColor']
                lines.append(f"  [{idx}]: {ratio:.1f} ❌ ({tc} on {bg})")
    
    # ─────────────────────────────────────────────────────────
    # TIMING section
    # ─────────────────────────────────────────────────────────
    timing_issues = validate_timing(layers, clip_duration)
    if timing_issues:
        lines.append("")
        lines.append("TIMING:")
        for issue in timing_issues:
            lines.append(f"  {issue}")
    
    # ─────────────────────────────────────────────────────────
    # ISSUES section - all issues in one place
    # ─────────────────────────────────────────────────────────
    all_issues = results.get('issues', []) + timing_issues
    
    if all_issues:
        lines.append("")
        lines.append("─" * 40)
        lines.append("ISSUES:")
        for issue in all_issues:
            lines.append(f"  {issue}")
    else:
        lines.append("")
        lines.append("─" * 40)
        lines.append("✓ All checks passed")
    
    return "\n".join(lines)


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
    """
    clip_id = state.get("clip_id")
    if not clip_id:
        return "ERROR: No clip_id in state"

    try:
        layers = json.loads(layers_json)
        if not isinstance(layers, list):
            return "ERROR: layers_json must be a JSON array"
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON: {e}"

    path = write_draft(clip_id, layers)
    print(f"   📝 Draft saved: {len(layers)} layers → {path.name}")
    return f"Draft saved with {len(layers)} layers. Call validate_clip_spec to check layout."


@tool
def edit_draft_spec(
    edits: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """
    Apply targeted edits to draft spec.

    Args:
        edits: JSON array of edit operations:
            [{"layer_index": 2, "field_path": "position.y", "value": 60}]

    Returns:
        Confirmation of applied edits
    """
    clip_id = state.get("clip_id")
    if not clip_id:
        return "ERROR: No clip_id in state"
    
    layers = read_draft(clip_id)
    if layers is None:
        return "ERROR: No draft found. Call draft_clip_spec first."
    
    try:
        edit_list = json.loads(edits)
        if not isinstance(edit_list, list):
            return "ERROR: edits must be a JSON array"
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON: {e}"
    
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
    
    write_draft(clip_id, layers)
    print(f"   ✏️  Applied {applied} edit(s)")
    return f"Applied {applied} edit(s). Call validate_clip_spec to verify."


@tool
def validate_clip_spec(
    state: Annotated[dict, InjectedState],
) -> str:
    """
    Validate draft spec: compute real bboxes, check spacing, contrast, timing.

    Returns:
        Concise validation report

    Layout Format:
      [index] type    WxH @ (centerX, centerY) 'content' fontSize

    Spacing Format:
      [a]↔[b]: gap_px  status

    Contrast Format:
      [index]: ratio  status
    """
    from src.tools.rag_recorder import rag_recorder

    clip_id = state.get("clip_id")
    if not clip_id:
        return "ERROR: No clip_id in state"

    layers = read_draft(clip_id)
    if layers is None:
        return "ERROR: No draft found. Call draft_clip_spec first."

    clip_duration = state.get("duration_frames", 150)

    # Run real measurement
    results = run_measure_script(layers)
    
    if results.get('error'):
        print(f"   ⚠️  Measurement error: {results.get('error')}")
        # Fall back to basic structure
        results = {
            "layers": [{"index": i, "type": l.get("type", "unknown"), "bbox": None} 
                       for i, l in enumerate(layers)],
            "spacing": [],
            "contrast": [],
            "issues": [f"⚠️ Measurement failed: {results.get('error')}"],
        }

    # Format report
    report = format_concise_report(results, layers, clip_duration)

    # Determine pass/fail
    all_issues = results.get('issues', [])
    timing_issues = validate_timing(layers, clip_duration)
    has_errors = any('❌' in str(i) for i in all_issues + timing_issues)
    has_warnings = any('⚠️' in str(i) for i in all_issues + timing_issues)
    
    passed = not has_errors

    # Record validation
    rag_recorder.record_validation(
        clip_id=clip_id,
        validation_results={
            "layers": results.get('layers', []),
            "spacing": results.get('spacing', []),
            "contrast": results.get('contrast', []),
            "issues": all_issues,
            "timing_issues": timing_issues,
        },
        passed=passed
    )

    if passed and not has_warnings:
        print("   ✓ Validation passed")
    elif passed:
        print("   ⚠️  Validation passed with warnings")
    else:
        print("   ❌ Validation failed")

    print(f"\n{report}\n")
    return report
