"""
Edit Assembler

Collects composed clip specs from the database and assembles them
into a complete VideoSpec for Remotion.

This is NOT an LLM agent - it's a deterministic assembly process.
The creative decisions were made by planner/composers.

## Simplification: Unified Image Type

All image layers are now just "image" type with a src path.
No special handling for "generated_image" - it doesn't exist anymore.
The composer already put the correct paths in place.

Assembler just reads the layers and passes them to Remotion.
"""
from typing import Optional
import json


def assemble_video_spec(
    video_project_id: str,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
) -> dict:
    """
    Assemble all composed specs into a VideoSpec.
    
    Reads from:
    - clip_tasks (status='composed')
    - video_projects (for metadata)
    
    No special handling needed for different image types.
    All images have src paths already set by the composer.
    
    Returns:
        Complete VideoSpec dict ready for Remotion
    """
    from db.supabase_client import get_client
    from tools.editor_tools import get_composed_clip_specs
    
    client = get_client()
    
    # Load project metadata
    project_result = client.table("video_projects").select("*").eq(
        "id", video_project_id
    ).single().execute()
    project = project_result.data
    
    if not project:
        raise ValueError(f"Project {video_project_id} not found")
    
    # Get composed specs
    clip_tasks = get_composed_clip_specs(video_project_id)
    
    if not clip_tasks:
        raise ValueError("No composed specs found. Run composers first.")
    
    # Build clips array
    clips = []
    for task in clip_tasks:
        spec = task.get("clip_spec", {})
        
        # Calculate start frame from start_time_s
        start_frame = int(task["start_time_s"] * fps)
        
        clip = {
            "id": task["id"],
            "startFrame": start_frame,
            "durationFrames": spec.get("durationFrames", int(task["duration_s"] * fps)),
            "layers": spec.get("layers", []),  # Layers already have correct src paths
            "composerNotes": spec.get("composerNotes", ""),
        }
        
        # Add transitions if present
        if spec.get("enterTransition"):
            clip["enterTransition"] = spec["enterTransition"]
        if spec.get("exitTransition"):
            clip["exitTransition"] = spec["exitTransition"]
        
        # NOTE: No special handling for generated_image layers anymore.
        # All images are just "image" type with src already set.
        # The composer took care of putting the right paths in place.
        
        clips.append(clip)
    
    # Sort by start frame
    clips = sorted(clips, key=lambda c: c["startFrame"])
    
    # Calculate total duration (max end frame across all clips)
    all_end_frames = []
    for clip in clips:
        all_end_frames.append(clip["startFrame"] + clip["durationFrames"])
    
    total_frames = max(all_end_frames) if all_end_frames else fps * 30  # Default 30s
    
    # Build the VideoSpec
    video_spec = {
        "meta": {
            "title": extract_title(project.get("user_input", "Product Video")),
            "durationFrames": total_frames,
            "fps": fps,
            "resolution": {
                "width": width,
                "height": height,
            },
        },
        "clips": clips,
        # Audio will be added in music phase
    }
    
    return video_spec


def extract_title(user_input: str) -> str:
    """Extract a reasonable title from user input."""
    # Simple heuristic: look for app name patterns
    words = user_input.split()
    
    # Just use first few meaningful words as title
    title_words = []
    skip_words = {"my", "app", "a", "an", "the", "for", "is", "i", "want", "need", "create", "make"}
    
    for word in words[:8]:
        clean = word.strip(".,!?\"'")
        if clean.lower() not in skip_words and len(clean) > 1:
            title_words.append(clean)
        if len(title_words) >= 3:
            break
    
    return " ".join(title_words) if title_words else "Product Video"


def validate_video_spec(spec: dict) -> tuple[bool, list[str]]:
    """
    Validate a VideoSpec for common issues.
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    # Check meta
    meta = spec.get("meta", {})
    if not meta.get("durationFrames"):
        issues.append("Missing durationFrames in meta")
    if not meta.get("fps"):
        issues.append("Missing fps in meta")
    
    clips = spec.get("clips", [])
    
    if not clips:
        issues.append("No clips defined")
    
    # Check each clip
    for i, clip in enumerate(clips):
        if not clip.get("durationFrames"):
            issues.append(f"Clip {i+1} missing durationFrames")
        
        layers = clip.get("layers", [])
        if not layers:
            issues.append(f"Clip {i+1} has no layers")
        
        # Check each layer
        for j, layer in enumerate(layers):
            layer_type = layer.get("type")
            
            # Valid types: background, image, text
            # NOTE: "generated_image" is no longer valid - use "image" instead
            if layer_type not in ["image", "text", "background"]:
                issues.append(f"Clip {i+1} layer {j+1} has invalid type: {layer_type}")
            
            if layer_type == "image" and not layer.get("src"):
                issues.append(f"Clip {i+1} image layer {j+1} missing src")
            
            if layer_type == "text" and not layer.get("content"):
                issues.append(f"Clip {i+1} text layer {j+1} missing content")
    
    return len(issues) == 0, issues


def save_video_spec_to_db(
    video_project_id: str,
    spec: dict,
    version: int = 1,
) -> str:
    """
    Save the VideoSpec to the database.
    
    Returns:
        The video_spec_id
    """
    from db.supabase_client import get_client
    
    client = get_client()
    
    result = client.table("video_specs").insert({
        "video_project_id": video_project_id,
        "spec": spec,
        "version": version,
        "render_status": "pending",
    }).execute()
    
    if result.data:
        return result.data[0]["id"]
    else:
        raise ValueError("Failed to save video spec")


def save_video_spec_to_file(spec: dict, output_path: str) -> str:
    """
    Save the VideoSpec to a JSON file for Remotion.
    
    Returns:
        The file path
    """
    with open(output_path, "w") as f:
        json.dump(spec, f, indent=2)
    
    return output_path


def print_spec_summary(spec: dict):
    """Print a human-readable summary of the video spec."""
    meta = spec.get("meta", {})
    clips = spec.get("clips", [])
    
    print(f"\n📹 Video Spec Summary")
    print(f"   Title: {meta.get('title', 'Untitled')}")
    print(f"   Duration: {meta.get('durationFrames', 0) / meta.get('fps', 30):.1f}s")
    print(f"   Resolution: {meta.get('resolution', {}).get('width', 0)}x{meta.get('resolution', {}).get('height', 0)}")
    print(f"   Clips: {len(clips)}")
    
    for i, clip in enumerate(clips, 1):
        layers = clip.get("layers", [])
        layer_types = [l.get("type", "?") for l in layers]
        duration_s = clip.get("durationFrames", 0) / meta.get("fps", 30)
        start_s = clip.get("startFrame", 0) / meta.get("fps", 30)
        
        print(f"\n   Clip {i}: {start_s:.1f}s - {start_s + duration_s:.1f}s ({duration_s:.1f}s)")
        print(f"      Layers: {', '.join(layer_types)}")
        
        # Show text content if present
        for layer in layers:
            if layer.get("type") == "text":
                print(f"      Text: \"{layer.get('content', '')}\"")


# ─────────────────────────────────────────────────────────────
# Node Function
# ─────────────────────────────────────────────────────────────

def edit_assembler_node(state: dict) -> dict:
    """
    LangGraph node: Assemble the final VideoSpec.
    """
    from db.supabase_client import get_client
    import os
    
    print("\n📦 Assembling video spec...")
    
    video_project_id = state["video_project_id"]
    
    try:
        # Assemble the spec
        spec = assemble_video_spec(video_project_id)
        
        # Validate
        is_valid, issues = validate_video_spec(spec)
        
        if not is_valid:
            print(f"   ⚠️  Validation issues:")
            for issue in issues:
                print(f"      - {issue}")
        
        # Print summary
        print_spec_summary(spec)
        
        # Save to DB
        spec_id = save_video_spec_to_db(video_project_id, spec)
        
        # Also save to file for Remotion
        specs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "specs")
        os.makedirs(specs_dir, exist_ok=True)
        spec_path = os.path.join(specs_dir, f"{video_project_id}.json")
        save_video_spec_to_file(spec, spec_path)
        
        # Update project status
        client = get_client()
        client.table("video_projects").update({
            "editor_status": "assembled",
        }).eq("id", video_project_id).execute()
        
        clip_count = len(spec.get("clips", []))
        total_layers = sum(len(c.get("layers", [])) for c in spec.get("clips", []))
        duration_s = spec["meta"]["durationFrames"] / spec["meta"]["fps"]
        
        print(f"\n✓ VideoSpec assembled:")
        print(f"   {clip_count} clips, {total_layers} total layers")
        print(f"   {duration_s:.1f}s total duration")
        print(f"   Saved to: {spec_path}")
        
        return {
            "video_spec": spec,
            "video_spec_id": spec_id,
        }
        
    except Exception as e:
        print(f"\n❌ Assembly failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "video_spec": None,
            "video_spec_id": None,
            "render_error": str(e),
        }
