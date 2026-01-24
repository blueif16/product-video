"""
Edit Assembler

Collects composed clip specs from the database and assembles them
into a complete VideoSpec for Remotion.

This is NOT an LLM agent - it's a deterministic assembly process.
The creative decisions were made by planner/composers.

## Asset Path Handling

The assembler copies all image assets to Remotion's public/assets directory
and updates paths to be relative paths that Remotion can access.
"""
from typing import Optional
import json
import os
import shutil
from pathlib import Path


def copy_asset_to_remotion(src_path: str, video_project_id: str) -> str:
    """
    Prepare an asset for Remotion rendering.
    
    Cloud-first: URLs pass through directly. Local files are copied to public/assets.
    
    Args:
        src_path: Asset source (URL or local path)
        video_project_id: Project ID for organizing local assets
    
    Returns:
        URL (unchanged) or relative path for Remotion
    """
    from tools.storage import is_remote_url
    
    # Cloud URLs pass through directly - Remotion handles them
    if is_remote_url(src_path):
        return src_path
    
    # Local file: copy to Remotion's public directory
    if not os.path.exists(src_path):
        print(f"   ⚠️  Asset not found: {src_path}")
        return src_path  # Return original, will fail in Remotion
    
    remotion_public = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "remotion", "public", "assets", video_project_id
    )
    os.makedirs(remotion_public, exist_ok=True)
    
    filename = os.path.basename(src_path)
    dest_path = os.path.join(remotion_public, filename)
    
    try:
        shutil.copy2(src_path, dest_path)
        return f"assets/{video_project_id}/{filename}"
    except Exception as e:
        print(f"   ⚠️  Failed to copy {src_path}: {e}")
        return src_path


def process_layer_assets(layer: dict, video_project_id: str) -> dict:
    """
    Process a layer and prepare assets for Remotion.
    
    Cloud URLs pass through. Local files are copied to public/assets.
    """
    from tools.storage import is_remote_url
    
    layer = layer.copy()  # Don't modify original
    
    if layer.get("type") == "image" and layer.get("src"):
        src = layer["src"]
        
        # Skip if already processed (relative path or URL)
        if src.startswith("assets/") or is_remote_url(src):
            if is_remote_url(src):
                print(f"   ☁️  Using cloud URL: ...{src[-40:]}")
            return layer
        
        # Process: copy local file or pass through URL
        new_path = copy_asset_to_remotion(src, video_project_id)
        layer["src"] = new_path
        
        if not is_remote_url(new_path):
            print(f"   📁 Copied: {os.path.basename(src)} → {new_path}")
    
    return layer


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
    
    Copies all image assets to Remotion's public directory and updates paths.
    
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
    
    print(f"   Processing {len(clip_tasks)} clips...")
    
    # Build clips array
    clips = []
    for task in clip_tasks:
        spec = task.get("clip_spec", {})
        
        # Calculate start frame from start_time_s
        start_frame = int(task["start_time_s"] * fps)
        
        # Process layers - copy assets and update paths
        layers = spec.get("layers", [])
        processed_layers = [
            process_layer_assets(layer, video_project_id)
            for layer in layers
        ]
        
        clip = {
            "id": task["id"],
            "startFrame": start_frame,
            "durationFrames": spec.get("durationFrames", int(task["duration_s"] * fps)),
            "layers": processed_layers,
            "composerNotes": spec.get("composerNotes", ""),
        }
        
        # Add transitions if present
        if spec.get("enterTransition"):
            clip["enterTransition"] = spec["enterTransition"]
        if spec.get("exitTransition"):
            clip["exitTransition"] = spec["exitTransition"]
        
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
    version: int = None,
) -> str:
    """
    Save the VideoSpec to the database.
    
    Automatically increments version if one exists.
    Uses upsert to avoid duplicate key errors when re-running.
    
    Returns:
        The video_spec_id
    """
    from db.supabase_client import get_client
    
    client = get_client()
    
    # Get the latest version for this project
    if version is None:
        existing = client.table("video_specs").select("version").eq(
            "video_project_id", video_project_id
        ).order("version", desc=True).limit(1).execute()
        
        if existing.data:
            version = existing.data[0]["version"] + 1
        else:
            version = 1
    
    # Use upsert with on_conflict to handle re-runs
    # This prevents duplicate key errors if you run the editor phase multiple times
    result = client.table("video_specs").upsert({
        "video_project_id": video_project_id,
        "spec": spec,
        "version": version,
        "render_status": "pending",
    }, on_conflict="video_project_id,version").execute()
    
    if result.data:
        print(f"   Saved as version {version}")
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
        # Assemble the spec (this will copy assets)
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
