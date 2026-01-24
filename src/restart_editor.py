#!/usr/bin/env python3
"""
Restart Editor Script

Runs the V2 editor with proper cleanup.
"""
from db.supabase_client import get_client
from editor import run_editor_standalone

# Replace with your actual project ID
PROJECT_ID = "09985d31-ece3-4528-9254-196959060070"


def cleanup_project(project_id: str):
    """Clean up old clip_tasks and video_specs for a fresh run."""
    client = get_client()
    
    print(f"\n🧹 Cleaning up project {project_id}...")
    
    # Delete old clip_tasks
    clip_result = client.table("clip_tasks").delete().eq(
        "video_project_id", project_id
    ).execute()
    clip_count = len(clip_result.data) if clip_result.data else 0
    print(f"   Deleted {clip_count} clip_tasks")
    
    # Delete old video_specs
    spec_result = client.table("video_specs").delete().eq(
        "video_project_id", project_id
    ).execute()
    spec_count = len(spec_result.data) if spec_result.data else 0
    print(f"   Deleted {spec_count} video_specs")
    
    # Delete old generated_assets
    gen_result = client.table("generated_assets").delete().eq(
        "video_project_id", project_id
    ).execute()
    gen_count = len(gen_result.data) if gen_result.data else 0
    print(f"   Deleted {gen_count} generated_assets")
    
    # Reset editor_status
    client.table("video_projects").update({
        "editor_status": None
    }).eq("id", project_id).execute()
    print(f"   Reset editor_status")
    
    print("   ✓ Cleanup complete\n")


if __name__ == "__main__":
    import sys
    
    # Check for --no-cleanup flag
    do_cleanup = "--no-cleanup" not in sys.argv
    
    if do_cleanup:
        cleanup_project(PROJECT_ID)
    
    result = run_editor_standalone(
        PROJECT_ID,
        include_render=True,   # Set False to skip Remotion rendering
        include_music=True,    # Set False to skip music generation
    )

    print("\n✅ Editor phase complete!")
    print(f"Video spec: {result.get('video_spec_id')}")
    print(f"Rendered: {result.get('render_path')}")
    print(f"Final video: {result.get('final_video_path')}")
