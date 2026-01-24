"""
Full Pipeline - Capture → Editor → Render → Music

Orchestrates the complete video generation flow:
1. Capture phase: Analyze app, capture screenshots/recordings
2. Editor phase: Plan timeline, compose clips, assemble VideoSpec
3. Render phase: Generate video with Remotion
4. Music phase: Generate aligned BGM, mux with video
"""
from typing import Optional


def run_full_pipeline(
    user_input: str,
    include_render: bool = True,
    include_music: bool = True,
) -> dict:
    """
    Run the complete video generation pipeline.
    
    Args:
        user_input: User's description of app and desired video
        include_render: Whether to render the video
        include_music: Whether to generate music (requires render)
    
    Returns:
        Final state with video_project_id, render_path, final_video_path, etc.
    """
    from orchestrator import run_pipeline
    from editor import run_editor_standalone
    
    # ─────────────────────────────────────────────────────────
    # Phase 1: Capture
    # ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("Phase 1: CAPTURE")
    print("="*60)
    
    capture_result = run_pipeline(user_input)
    
    video_project_id = capture_result.get("video_project_id")
    
    if not video_project_id:
        print("\n❌ Capture phase failed - no project ID returned")
        return capture_result
    
    # Check if capture was successful
    status = capture_result.get("status")
    if status not in ["aggregated", "completed"]:
        print(f"\n⚠️  Capture phase incomplete (status: {status})")
        print(f"   Project ID: {video_project_id}")
        print(f"   You can resume with: python -m src.main --phase editor --project-id {video_project_id}")
        return capture_result
    
    print(f"\n✅ Capture complete!")
    print(f"   Project ID: {video_project_id}")
    
    # ─────────────────────────────────────────────────────────
    # Phase 2-4: Editor (includes render + music)
    # ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("Phase 2: EDITOR → RENDER → MUSIC")
    print("="*60)
    
    editor_result = run_editor_standalone(
        video_project_id,
        include_render=include_render,
        include_music=include_music,
    )
    
    # Merge results
    final_result = {
        **capture_result,
        **editor_result,
    }
    
    # ─────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("🎉 PIPELINE COMPLETE")
    print("="*60)
    
    print(f"\n   Project ID: {video_project_id}")
    
    if final_result.get("final_video_path"):
        print(f"   🎬 Final video (with music): {final_result['final_video_path']}")
    elif final_result.get("render_path"):
        print(f"   🎬 Rendered video: {final_result['render_path']}")
    
    if final_result.get("audio_path"):
        print(f"   🎵 Audio: {final_result['audio_path']}")
    
    if final_result.get("video_spec"):
        clips = final_result["video_spec"].get("clips", [])
        print(f"   📋 VideoSpec: {len(clips)} clips")
    
    return final_result


def run_from_capture_result(
    capture_result: dict,
    include_render: bool = True,
    include_music: bool = True,
) -> dict:
    """
    Continue pipeline from a capture result.
    
    Useful when capture completed but editor hasn't run yet.
    """
    from editor import run_editor_standalone
    
    video_project_id = capture_result.get("video_project_id")
    
    if not video_project_id:
        raise ValueError("No video_project_id in capture result")
    
    editor_result = run_editor_standalone(
        video_project_id,
        include_render=include_render,
        include_music=include_music,
    )
    
    return {
        **capture_result,
        **editor_result,
    }
