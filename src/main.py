"""
Main entry point. Single text input, human-in-the-loop when needed.

Handles graceful shutdown on Ctrl+C with optional database cleanup.
"""
import sys
import signal
import atexit
from typing import Optional

from orchestrator import run_pipeline, get_session, end_session
from db.supabase_client import cleanup_session


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║           PRODUCT VIDEO PIPELINE                             ║
║                                                              ║
║   Describe your app and desired video.                       ║
║   I'll capture assets and (soon) generate the video.         ║
║                                                              ║
║   Press Ctrl+C to stop gracefully.                           ║
╚══════════════════════════════════════════════════════════════╝
"""


# ─────────────────────────────────────────────────────────────
# Graceful Shutdown Handler
# ─────────────────────────────────────────────────────────────

_shutdown_in_progress = False


def handle_shutdown(signum: Optional[int] = None, frame=None) -> None:
    """
    Handle Ctrl+C (SIGINT) gracefully.
    
    1. Stop the pipeline
    2. Show what was created
    3. Ask user if they want to clean up
    4. Clean up if requested
    """
    global _shutdown_in_progress
    
    # Prevent multiple handlers
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
    
    # Show session summary
    summary = session.get_summary()
    
    print(f"\nSession Status:")
    print(f"  Stage: {summary['stage']}")
    print(f"  Video Project: {summary['video_project_id'][:8] + '...' if summary['video_project_id'] else 'None'}")
    print(f"  Tasks Created: {summary['total_tasks']}")
    print(f"  Tasks Completed: {summary['completed_tasks']}")
    print(f"  Tasks Pending: {summary['pending_tasks']}")
    
    # Only ask about cleanup if there's something to clean
    if summary['video_project_id'] or summary['total_tasks'] > 0:
        print(f"\n" + "-" * 60)
        print("DATABASE CLEANUP")
        print("-" * 60)
        print(f"\nRecords created this session:")
        if summary['video_project_id']:
            print(f"  • 1 video_project record")
        if summary['total_tasks'] > 0:
            print(f"  • {summary['total_tasks']} capture_task records")
        
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
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Handle terminal close (SIGHUP) on Unix
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, handle_shutdown)
    
    # Handle termination request (SIGTERM)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Register cleanup on normal exit too
    atexit.register(lambda: end_session())


# ─────────────────────────────────────────────────────────────
# Main Entry Points
# ─────────────────────────────────────────────────────────────

def main():
    """Interactive entry point."""
    setup_signal_handlers()
    
    print(BANNER)
    
    print("Describe your project and what kind of video you want:")
    print("(Include: project path, what the app does, video goals)")
    print()
    
    # Handle multi-line input
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
        # Ctrl+C during input - just exit cleanly
        print("\n\nCancelled.")
        sys.exit(0)
    
    user_input = "\n".join(lines).strip()
    
    if not user_input:
        print("No input provided. Exiting.")
        return
    
    print()
    print("-" * 60)
    print()
    
    try:
        result = run_pipeline(user_input)
        
        # Normal completion
        session = get_session()
        if not session.was_interrupted:
            print("\n✅ Pipeline completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {e}")
        handle_shutdown()


def run_from_string(user_input: str) -> dict:
    """
    Programmatic entry point.
    
    Note: Signal handlers are set up, but Ctrl+C behavior may vary
    depending on the calling context.
    """
    setup_signal_handlers()
    return run_pipeline(user_input)


if __name__ == "__main__":
    main()
