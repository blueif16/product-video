#!/usr/bin/env python3
"""
Test Editor Pipeline - Text Animations Only

Creates a minimal DB entry and runs the editor phase to generate
a video with text animations. No real assets needed.

Usage:
    python scripts/test_editor_text_only.py [config_name]

    config_name: Optional. Name of the config in video_configs.json (default: "begin")
                 Available: "begin", "closet_ai"

What it does:
    1. Creates a video_project entry in Supabase (no capture_tasks needed)
    2. Runs the editor phase (planner → composer → assembler → render → music)
    3. On exit, asks whether to clean up DB entries

Note: Text-only videos have no captured assets. The planner creates
text-only clips based on the user_input description.
"""
import sys
import os
import uuid
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.supabase_client import get_client
from pathlib import Path


def load_video_config(config_name: str = "Closet AI") -> dict:
    """Load video config from video_configs.json"""
    config_path = Path(__file__).parent / "video_configs.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        configs = json.load(f)

    if config_name not in configs:
        available = ", ".join(configs.keys())
        raise ValueError(f"Config '{config_name}' not found. Available: {available}")

    return configs[config_name]


def create_test_project(config_name: str = "begin") -> str:
    """
    Create a test video project ready for editor phase.

    Text-only videos don't need capture_tasks - the planner creates
    clips with text layers based on the user_input description.

    Returns the project ID.
    """
    client = get_client()
    project_id = str(uuid.uuid4())

    # Load video config
    config = load_video_config(config_name)
    user_input = config["user_input"]
    analysis_summary = config["analysis_summary"]

    # Create project (no capture_tasks needed for text-only)
    project_data = {
        "id": project_id,
        "user_input": user_input.strip(),
        "project_path": None,  # No project path for text-only
        "app_bundle_id": None,
        "analysis_summary": analysis_summary.strip(),
        "status": "aggregated",  # Ready for editor phase
        "editor_status": None,
    }

    result = client.table("video_projects").insert(project_data).execute()

    if not result.data:
        raise RuntimeError("Failed to create video project")

    print(f"✓ Created video_project: {project_id}")
    print(f"   Config: {config_name} ({config['product_name']}, {config['duration']}s)")
    print(f"   (Text-only - no capture_tasks needed)")

    return project_id


def cleanup_project(project_id: str):
    """Clean up all DB entries for a project."""
    client = get_client()
    
    # Delete in order (foreign keys)
    client.table("generated_assets").delete().eq("video_project_id", project_id).execute()
    client.table("clip_tasks").delete().eq("video_project_id", project_id).execute()
    client.table("capture_tasks").delete().eq("video_project_id", project_id).execute()
    client.table("video_specs").delete().eq("video_project_id", project_id).execute()
    client.table("video_projects").delete().eq("id", project_id).execute()
    
    print(f"✓ Cleaned up project {project_id}")


def check_remotion_setup() -> bool:
    """Check if Remotion is ready to render."""
    remotion_dir = Path(__file__).parent.parent / "remotion"
    
    if not remotion_dir.exists():
        print(f"❌ Remotion directory not found at {remotion_dir}")
        return False
    
    if not (remotion_dir / "node_modules").exists():
        print(f"❌ Remotion dependencies not installed")
        print(f"\n   Run: cd {remotion_dir} && npm install")
        return False
    
    if not (remotion_dir / "scripts" / "render.ts").exists():
        print(f"❌ Remotion render script not found")
        return False
    
    return True


def check_elevenlabs_setup() -> bool:
    """Check if ElevenLabs API key is set."""
    from config import Config
    
    if Config.ELEVENLABS_API_KEY:
        return True
    
    print("⚠️  ELEVENLABS_API_KEY not set - music will be skipped")
    return False


def main():
    """Run the test."""
    # Parse command line args
    config_name = sys.argv[1] if len(sys.argv) > 1 else "begin"

    print("\n" + "=" * 60)
    print("🧪 EDITOR PIPELINE TEST - TEXT ANIMATIONS")
    print("=" * 60)
    print(f"📝 Using config: {config_name}")

    # Pre-flight checks
    print("\n📋 Pre-flight checks...")
    
    remotion_ok = check_remotion_setup()
    if remotion_ok:
        print("✓ Remotion setup OK")
    else:
        print("\n⚠️  Remotion not ready - video will not render")
        print("   Pipeline will still run and create VideoSpec")
        response = input("\nContinue anyway? [y/N]: ").strip().lower()
        if response != 'y':
            sys.exit(0)
    
    elevenlabs_ok = check_elevenlabs_setup()
    if elevenlabs_ok:
        print("✓ ElevenLabs API key found")
    
    # Check Supabase connection
    try:
        client = get_client()
        print("✓ Supabase connection OK")
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print("\nMake sure .env has SUPABASE_URL and SUPABASE_KEY set.")
        sys.exit(1)
    
    # Create test project
    print("\n📦 Creating test project...")
    project_id = None
    try:
        project_id = create_test_project(config_name)
    except Exception as e:
        print(f"❌ Failed to create project: {e}")
        sys.exit(1)
    
    print(f"\n🚀 Starting editor phase for project: {project_id}")
    print("-" * 60)
    
    # Import after path setup
    from main import run_editor_phase, setup_signal_handlers
    from orchestrator import get_session
    
    # Set up signal handlers for graceful shutdown
    setup_signal_handlers()
    
    # Track the project in session for cleanup
    session = get_session()
    session.video_project_id = project_id
    
    try:
        # Run editor phase with render AND music (automatic, no prompts)
        result = run_editor_phase(
            project_id=project_id,
            test_mode=False,         # Use real DB
            include_render=True,     # Try to render video
            include_music=elevenlabs_ok,  # Generate music if API key available
        )
        
        print("\n" + "=" * 60)
        print("✅ EDITOR PHASE COMPLETE")
        print("=" * 60)
        
        # Report results
        if result.get("final_video_path"):
            print(f"\n🎬 Final video (with music): {result['final_video_path']}")
        elif result.get("render_path"):
            print(f"\n🎬 Video rendered: {result['render_path']}")
            if elevenlabs_ok and not result.get("audio_path"):
                print(f"   ⚠️  Music generation may have failed")
        elif result.get("video_spec"):
            print(f"\n📋 VideoSpec created (render may have been skipped)")
            spec = result.get("video_spec", {})
            clips = spec.get("clips", [])
            print(f"   Clips: {len(clips)}")
        
        if result.get("audio_path"):
            print(f"🎵 Audio generated: {result['audio_path']}")
        
        # Ask about cleanup
        print("\n" + "-" * 60)
        response = input("Delete test project from DB? [y/N]: ").strip().lower()
        if response == 'y':
            cleanup_project(project_id)
        else:
            print(f"\n📦 Project kept. ID: {project_id}")
            print(f"   Run again: python -m src.main --phase editor --project-id {project_id}")
        
    except KeyboardInterrupt:
        # Handled by signal handler in main.py
        pass
    except Exception as e:
        print(f"\n❌ Error during editor phase: {e}")
        import traceback
        traceback.print_exc()
        
        # Still offer cleanup
        if project_id:
            print("\n" + "-" * 60)
            response = input("Delete test project from DB? [y/N]: ").strip().lower()
            if response == 'y':
                cleanup_project(project_id)


if __name__ == "__main__":
    main()
