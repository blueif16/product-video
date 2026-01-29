"""
StreamLine Video Pipeline - Main Entry Point

Usage:
    # Full pipeline (capture → edit → render → music)
    python -m src.main
    
    # Capture only
    python -m src.main --phase capture
    
    # Editor only (requires completed capture)
    python -m src.main --phase editor --project-id <uuid>

    # Render only (requires video_spec in DB)
    python -m src.main --phase render --project-id <uuid>

    # Music only (add music to existing render)
    python -m src.main --phase music --project-id <uuid>
    python -m src.main --phase music --project-id <uuid> --video-path /path/to/video.mp4
    
    # Editor test mode (mock data, no DB)
    python -m src.main --phase editor --test
    
    # Skip rendering (and music)
    python -m src.main --no-render
    
    # Skip music generation
    python -m src.main --no-music

Handles graceful shutdown on Ctrl+C with optional database cleanup.
"""
import sys
import signal
import atexit
import argparse
from typing import Optional

from src.orchestrator import run_pipeline, get_session, end_session
from src.db.supabase_client import cleanup_session


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║           STREAMLINE VIDEO PIPELINE                          ║
║                                                              ║
║   Describe your app and desired video.                       ║
║   I'll capture assets and generate the video.                ║
║                                                              ║
║   Press Ctrl+C to stop gracefully.                           ║
╚══════════════════════════════════════════════════════════════╝
"""


# ─────────────────────────────────────────────────────────────
# Graceful Shutdown Handler
# ─────────────────────────────────────────────────────────────

_shutdown_in_progress = False


def handle_shutdown(signum: Optional[int] = None, frame=None) -> None:
    """Handle Ctrl+C (SIGINT) gracefully."""
    global _shutdown_in_progress
    
    if _shutdown_in_progress:
        print("\n\n⚠️  Force quit. Some records may remain in database.")
        sys.exit(1)
    
    _shutdown_in_progress = True
    
    print("\n")
    print("=" * 60)
    print("🛑 INTERRUPT RECEIVED")
    print("=" * 60)
    
    session = get_session()
    session.was_interrupted = True
    
    summary = session.get_summary()
    
    print(f"\nSession Status:")
    print(f"  Stage: {summary['stage']}")
    print(f"  Video Project: {summary['video_project_id'][:8] + '...' if summary['video_project_id'] else 'None'}")
    print(f"  Tasks Created: {summary['total_tasks']}")
    print(f"  Tasks Completed: {summary['completed_tasks']}")
    print(f"  Tasks Pending: {summary['pending_tasks']}")
    
    if summary['video_project_id'] or summary['total_tasks'] > 0:
        print(f"\n" + "-" * 60)
        print("DATABASE CLEANUP")
        print("-" * 60)
        print(f"\nOptions:")
        print(f"  [d] Delete all records from this session")
        print(f"  [k] Keep records (can resume or inspect later)")
        print(f"  [Enter] Keep records (default)")
        
        try:
            response = input("\nYour choice: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            response = ""
        
        if response == 'd':
            print(f"\n🗑️  Cleaning up...")
            result = cleanup_session(
                video_project_id=summary['video_project_id'],
                task_ids=session.task_ids
            )
            
            if result['video_project']:
                print(f"  ✓ Deleted video project")
            if result['tasks'] > 0:
                print(f"  ✓ Deleted {result['tasks']} capture tasks")
            print(f"\n✅ Cleanup complete.")
        else:
            print(f"\n📦 Records preserved.")
            if summary['video_project_id']:
                print(f"   Video Project ID: {summary['video_project_id']}")
    else:
        print(f"\nNo database records created yet.")
    
    print(f"\n" + "=" * 60)
    print("Goodbye!")
    print("=" * 60 + "\n")
    
    end_session()
    sys.exit(0)


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, handle_shutdown)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    atexit.register(lambda: end_session())


# ─────────────────────────────────────────────────────────────
# Phase Runners
# ─────────────────────────────────────────────────────────────

def get_user_input() -> str:
    """Interactive prompt for user input."""
    print("Describe your project and what kind of video you want:")
    print("(Include: project path, what the app does, video goals)")
    print("(Press Enter twice when done)")
    print()
    
    lines = []
    print("> ", end="", flush=True)
    
    try:
        while True:
            line = input()
            if line.strip() == "":
                if lines:
                    break
                continue
            lines.append(line)
            print("  ", end="", flush=True)
    except EOFError:
        pass
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    
    return "\n".join(lines).strip()


def run_capture_phase(user_input: str) -> dict:
    """Run capture phase only."""
    print("\n" + "="*60)
    print("Phase: CAPTURE")
    print("="*60)
    
    result = run_pipeline(user_input)
    
    session = get_session()
    if not session.was_interrupted:
        print("\n✅ Capture phase completed!")
        if result.get("video_project_id"):
            print(f"\n📋 To continue with editing:")
            print(f"   python -m src.main --phase editor --project-id {result['video_project_id']}")
    
    return result


def run_editor_phase(
    project_id: str = None,
    test_mode: bool = False,
    include_render: bool = True,
    include_music: bool = True,
) -> dict:
    """Run editor phase only."""
    from .editor import run_editor_standalone, run_editor_test
    
    print("\n" + "="*60)
    print("Phase: EDITOR" + (" (TEST MODE)" if test_mode else ""))
    if include_music:
        print("       Music: ENABLED (will generate after render)")
    else:
        print("       Music: DISABLED")
    print("="*60)
    
    if test_mode:
        print("\n🧪 Running with test data (no database)...")
        result = run_editor_test(
            include_render=include_render,
            include_music=include_music,
        )
    else:
        if not project_id:
            print("Error: --project-id required for editor phase")
            print("       Or use --test for test mode")
            sys.exit(1)
        
        print(f"\n📂 Loading project: {project_id}")
        result = run_editor_standalone(
            project_id,
            include_render=include_render,
            include_music=include_music,
        )
    
    print("\n✅ Editor phase completed!")
    
    # Report final output
    if result.get("final_video_path"):
        print(f"   🎬 Final video (with music): {result['final_video_path']}")
    elif result.get("render_path"):
        print(f"   🎬 Video rendered: {result['render_path']}")
        if include_music:
            print(f"   ⚠️  Music generation may have failed")
    elif result.get("video_spec"):
        print(f"   📋 VideoSpec created (render {'skipped' if not include_render else 'failed'})")
    
    if result.get("audio_path"):
        print(f"   🎵 Audio: {result['audio_path']}")
    
    return result


def run_music_phase(project_id: str, video_path: str = None) -> dict:
    """
    Run music generation phase only.

    This adds music to an already-rendered video.
    """
    from .editor import run_music_only
    from pathlib import Path

    print("\n" + "="*60)
    print("Phase: MUSIC")
    print("="*60)

    if not project_id:
        print("Error: --project-id required for music phase")
        sys.exit(1)

    # If no video_path provided, look for the rendered video
    if not video_path:
        default_path = Path(f"assets/renders/{project_id}.mp4")
        if default_path.exists():
            video_path = str(default_path)
            print(f"\n📂 Found rendered video: {video_path}")
        else:
            print(f"\n⚠️  No video found at {default_path}")
            print("   Music will be generated without muxing")
    else:
        print(f"\n📂 Using video: {video_path}")

    print(f"📂 Loading project: {project_id}")

    result = run_music_only(project_id, video_path=video_path)

    print("\n✅ Music phase completed!")

    if result.get("final_video_path"):
        print(f"   🎬 Final video (with music): {result['final_video_path']}")
    if result.get("audio_path"):
        print(f"   🎵 Audio: {result['audio_path']}")

    return result


def run_render_phase(
    project_id: str,
    include_music: bool = True,
) -> dict:
    """
    Run render phase only (load video_spec from DB and render).

    This assumes video_spec is already in the database.
    Uses run_assembly_only to skip editor, then renders.
    """
    from langgraph.graph import StateGraph, START, END
    from .editor.core.state import EditorState
    from .db.supabase_client import get_supabase

    print("\n" + "="*60)
    print("Phase: RENDER")
    if include_music:
        print("       Music: ENABLED (will generate after render)")
    else:
        print("       Music: DISABLED")
    print("="*60)

    if not project_id:
        print("Error: --project-id required for render phase")
        sys.exit(1)

    print(f"\n📂 Loading project: {project_id}")

    # Load video_spec from video_specs table (latest version)
    supabase = get_supabase()
    response = supabase.table("video_specs").select("spec").eq(
        "video_project_id", project_id
    ).order("version", desc=True).limit(1).execute()

    if not response.data or not response.data[0].get("spec"):
        print(f"❌ Error: No video_spec found for project {project_id}")
        print("   Run editor phase first to generate video_spec")
        sys.exit(1)

    video_spec = response.data[0]["spec"]
    print(f"   ✓ Loaded video_spec with {len(video_spec.get('clips', []))} clips")

    # Build minimal graph: render → [music]
    builder = StateGraph(EditorState)

    try:
        from .renderer.render_client import remotion_render_node
        builder.add_node("render", remotion_render_node)
    except ImportError:
        print("❌ Error: Render client not available")
        sys.exit(1)

    if include_music:
        from .editor.core.music_planner import music_planner_node
        from .tools.music_generator import music_generator_node, mux_audio_video_node

        builder.add_node("music_plan", music_planner_node)
        builder.add_node("music_generate", music_generator_node)
        builder.add_node("mux_audio", mux_audio_video_node)

        builder.add_edge(START, "render")
        builder.add_edge("render", "music_plan")
        builder.add_edge("music_plan", "music_generate")
        builder.add_edge("music_generate", "mux_audio")
        builder.add_edge("mux_audio", END)
    else:
        builder.add_edge(START, "render")
        builder.add_edge("render", END)

    graph = builder.compile()

    # Create initial state with video_spec
    initial_state = {
        "video_project_id": project_id,
        "video_spec": video_spec,
    }

    config = {"configurable": {"thread_id": f"render-{project_id}"}}
    result = graph.invoke(initial_state, config=config)

    print("\n✅ Render phase completed!")

    if result.get("final_video_path"):
        print(f"   🎬 Final video (with music): {result['final_video_path']}")
    elif result.get("render_path"):
        print(f"   🎬 Video rendered: {result['render_path']}")
        if include_music:
            print(f"   ⚠️  Music generation may have failed")

    if result.get("audio_path"):
        print(f"   🎵 Audio: {result['audio_path']}")

    return result


def run_full_pipeline_interactive(
    user_input: str,
    include_render: bool = True,
    include_music: bool = True,
) -> dict:
    """Run complete pipeline."""
    from .pipeline import run_full_pipeline
    
    return run_full_pipeline(
        user_input,
        include_render=include_render,
        include_music=include_music,
    )


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────

def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="StreamLine Video Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive full pipeline
  python -m src.main

  # Capture phase only
  python -m src.main --phase capture

  # Editor phase (from completed capture)
  python -m src.main --phase editor --project-id abc-123

  # Render phase (from existing video_spec)
  python -m src.main --phase render --project-id abc-123

  # Editor without music
  python -m src.main --phase editor --project-id abc-123 --no-music

  # Music phase only (add music to existing render)
  python -m src.main --phase music --project-id abc-123
  python -m src.main --phase music --project-id abc-123 --video-path /path/to/video.mp4

  # Editor test mode
  python -m src.main --phase editor --test

  # Full pipeline without rendering
  python -m src.main --no-render

  # Non-interactive with input string
  python -m src.main --input "30s promo for FocusFlow at ~/Code/FocusFlow"
        """
    )
    
    parser.add_argument(
        "--phase",
        choices=["capture", "editor", "render", "music", "full"],
        default="full",
        help="Which phase to run (default: full)"
    )
    
    parser.add_argument(
        "--project-id",
        help="Project UUID (required for editor/music phase)"
    )
    
    parser.add_argument(
        "--video-path",
        help="Path to rendered video (optional for music phase)"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run with test data (no database required)"
    )
    
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip the Remotion render step"
    )
    
    parser.add_argument(
        "--no-music",
        action="store_true",
        help="Skip music generation"
    )
    
    parser.add_argument(
        "--input",
        help="User input string (skips interactive prompt)"
    )
    
    args = parser.parse_args()
    
    setup_signal_handlers()
    
    # Determine music setting
    include_music = not args.no_music
    # If no render, no music either
    if args.no_render:
        include_music = False
    
    try:
        # ─────────────────────────────────────────────────────
        # Music Phase (add music to existing video)
        # ─────────────────────────────────────────────────────
        if args.phase == "music":
            run_music_phase(
                project_id=args.project_id,
                video_path=args.video_path,
            )

        # ─────────────────────────────────────────────────────
        # Render Phase (render from existing video_spec)
        # ─────────────────────────────────────────────────────
        elif args.phase == "render":
            run_render_phase(
                project_id=args.project_id,
                include_music=include_music,
            )

        # ─────────────────────────────────────────────────────
        # Editor Phase
        # ─────────────────────────────────────────────────────
        elif args.phase == "editor":
            run_editor_phase(
                project_id=args.project_id,
                test_mode=args.test,
                include_render=not args.no_render,
                include_music=include_music,
            )
        
        # ─────────────────────────────────────────────────────
        # Capture Phase
        # ─────────────────────────────────────────────────────
        elif args.phase == "capture":
            print(BANNER)
            user_input = args.input or get_user_input()
            
            if not user_input:
                print("No input provided. Exiting.")
                return
            
            run_capture_phase(user_input)
        
        # ─────────────────────────────────────────────────────
        # Full Pipeline
        # ─────────────────────────────────────────────────────
        else:
            print(BANNER)
            user_input = args.input or get_user_input()
            
            if not user_input:
                print("No input provided. Exiting.")
                return
            
            run_full_pipeline_interactive(
                user_input,
                include_render=not args.no_render,
                include_music=include_music,
            )
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        handle_shutdown()


def run_from_string(
    user_input: str,
    phase: str = "full",
    include_render: bool = True,
    include_music: bool = True,
) -> dict:
    """
    Programmatic entry point.
    
    Args:
        user_input: Description of app and video
        phase: "capture", "editor", or "full"
        include_render: Whether to render the video
        include_music: Whether to generate music (requires render)
    
    Returns:
        Final pipeline state
    """
    setup_signal_handlers()
    
    if phase == "capture":
        return run_capture_phase(user_input)
    elif phase == "editor":
        # For editor, user_input is actually the project_id
        return run_editor_phase(
            project_id=user_input,
            include_render=include_render,
            include_music=include_music,
        )
    else:
        from .pipeline import run_full_pipeline
        return run_full_pipeline(
            user_input,
            include_render=include_render,
            include_music=include_music,
        )


if __name__ == "__main__":
    main()
