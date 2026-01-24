#!/usr/bin/env python3
"""
Add Music to Rendered Video

Simple script to add AI-generated music to an existing rendered video.

Usage:
    python scripts/add_music.py <project_id>
    python scripts/add_music.py <project_id> --video /path/to/video.mp4
    
Example:
    python scripts/add_music.py 09985d31-ece3-4528-9254-196959060070
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Add AI-generated music to a rendered video",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "project_id",
        help="Video project UUID"
    )
    
    parser.add_argument(
        "--video", "-v",
        help="Path to rendered video (auto-detected if not provided)"
    )
    
    parser.add_argument(
        "--no-mux",
        action="store_true",
        help="Only generate audio, don't mux with video"
    )
    
    args = parser.parse_args()
    
    # Find video path
    video_path = args.video
    if not video_path:
        default_path = Path(f"assets/renders/{args.project_id}.mp4")
        if default_path.exists():
            video_path = str(default_path)
            print(f"📂 Found rendered video: {video_path}")
        else:
            print(f"⚠️  No video found at {default_path}")
            if args.no_mux:
                print("   Will generate audio only (--no-mux)")
            else:
                print("   Will generate audio only (no video to mux)")
                video_path = None
    
    # Import and run
    from editor import run_music_only
    
    print(f"\n{'='*60}")
    print(f"🎵 Adding Music to Project: {args.project_id}")
    print(f"{'='*60}\n")
    
    result = run_music_only(
        args.project_id,
        video_path=None if args.no_mux else video_path
    )
    
    print(f"\n{'='*60}")
    print("✅ Complete!")
    print(f"{'='*60}")
    
    if result.get("final_video_path"):
        print(f"\n🎬 Final video (with music):")
        print(f"   {result['final_video_path']}")
    
    if result.get("audio_path"):
        print(f"\n🎵 Audio track:")
        print(f"   {result['audio_path']}")
    
    return result


if __name__ == "__main__":
    main()
