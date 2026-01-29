#!/usr/bin/env python3
"""
Composer V2 Test Harness

Creates ONE clip task with realistic planner-style notes,
runs composer, assembles VideoSpec, RENDERS, and outputs final MP4.

Usage:
    cd /Users/tk/Desktop/productvideo/src
    python test_composer_v2.py
"""
import sys
import uuid
import json
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.db.supabase_client import get_client
from src.editor.composers.v2 import compose_single_clip_node
from src.editor.core.assembler import edit_assembler_node
from src.renderer.render_client import render_video


def create_test_clip_task():
    """
    Create test project + ONE clip task with planner-style composer_notes.
    """
    print("\n" + "="*70)
    print("🎬 CREATING TEST CLIP TASK")
    print("="*70)
    
    client = get_client()
    
    # Create test project (direct DB insert)
    project_result = client.table("video_projects").insert({
        "user_input": "Fashion app promo, elegant premium style",
        "project_path": "test://project",
        "app_bundle_id": "com.test.fashionapp",
        "analysis_summary": "Fashion/clothing app with elegant product displays",
        "status": "aggregated",
    }).execute()
    
    project_id = project_result.data[0]["id"]
    print(f"✓ Project: {project_id[:8]}...")
    
    # Create capture task with real image URL
    client.table("capture_tasks").insert({
        "video_project_id": project_id,
        "task_description": "App screenshot",
        "capture_type": "screenshot",
        "asset_path": "download (2) [1170×2532, screenshot]",
        "asset_url": "https://pdifoxkgolxeufdtpolt.supabase.co/storage/v1/object/public/captures/uploads/pending/tmp0tirqqkz.png",
        "status": "completed",
    }).execute()
    
    # EXACT composerNotes from clip 1 in the problematic video log
    composer_notes = """Layout Type C with centered text stack. Headline uses a kinetic word-stagger reveal. Subtext follows with a snappy slide-up. Background features subtle accent blue orbs positioned in corners to maintain high text contrast and legibility. Vertical spacing between headline and subtext is calculated at ~11% to ensure clear hierarchy without crowding."""
    
    clip_result = client.table("clip_tasks").insert({
        "video_project_id": project_id,
        "asset_path": "download (2) [1170×2532, screenshot]",
        "asset_url": "https://pdifoxkgolxeufdtpolt.supabase.co/storage/v1/object/public/captures/uploads/pending/tmp0tirqqkz.png",
        "start_time_s": 0.0,
        "duration_s": 5.0,
        "composer_notes": composer_notes,
        "status": "pending",
    }).execute()
    
    clip_id = clip_result.data[0]["id"]
    
    print(f"✓ Clip task: {clip_id[:8]}...")
    print(f"   Duration: 5.0s (150 frames)")
    print(f"\n   Composer notes:\n{composer_notes}\n")
    
    return project_id, clip_id


def run_test():
    """Full test: create → compose → assemble → RENDER."""
    
    # Step 1: Create test clip task
    project_id, clip_id = create_test_clip_task()
    
    # Step 2: Run ACTUAL composer agent (full autonomy)
    print("="*70)
    print("🎨 RUNNING COMPOSER (full creative autonomy)")
    print("="*70)
    
    compose_single_clip_node({
        "clip_id": clip_id,
        "video_project_id": project_id,
    })
    
    # Check composer output
    client = get_client()
    result = client.table("clip_tasks").select("clip_spec, status").eq("id", clip_id).single().execute()
    
    if not result.data or not result.data.get("clip_spec"):
        print("\n❌ Composer FAILED - no clip_spec created")
        return
    
    spec = result.data["clip_spec"]
    layers = spec.get("layers", [])
    
    print(f"\n✓ Composer output: {len(layers)} layers")
    for i, layer in enumerate(layers, 1):
        ltype = layer.get("type")
        if ltype == "text":
            pos = layer.get('position', {})
            print(f"   {i}. text: \"{layer.get('content')}\" at {pos} (zIndex={layer.get('zIndex')})")
        elif ltype == "image":
            pos = layer.get('position', {})
            device = layer.get('device', 'none')
            scale = layer.get('scale', 1.0)
            transform = layer.get('transform', {})
            print(f"   {i}. image: pos={pos}, scale={scale}, device={device}, transform={transform.get('type')} (zIndex={layer.get('zIndex')})")
        elif ltype == "background":
            has_orbs = layer.get('orbs', False)
            gradient = layer.get('gradient')
            if gradient:
                print(f"   {i}. background: gradient {gradient.get('colors')} (zIndex={layer.get('zIndex')})")
            else:
                print(f"   {i}. background: color={layer.get('color', 'N/A')}, orbs={has_orbs} (zIndex={layer.get('zIndex')})")
    
    # Step 3: Assemble VideoSpec
    print("\n" + "="*70)
    print("📦 ASSEMBLING VIDEO SPEC")
    print("="*70)
    
    asm_result = edit_assembler_node({"video_project_id": project_id})
    video_spec = asm_result.get("video_spec")
    
    if not video_spec:
        print("❌ Assembler FAILED")
        return
    
    print(f"✓ VideoSpec assembled:")
    print(f"   Clips: {len(video_spec.get('clips', []))}")
    print(f"   Duration: {video_spec.get('meta', {}).get('durationFrames', 0)} frames")
    
    # Step 4: RENDER THE VIDEO
    print("\n" + "="*70)
    print("🎥 RENDERING VIDEO WITH REMOTION")
    print("="*70)
    
    success, output_path, error = render_video(
        video_spec=video_spec,
        output_filename=f"test_{project_id[:8]}.mp4",
        composition_id="ProductVideo",
        codec="h264",
        crf=18,
    )
    
    if success:
        print("\n" + "="*70)
        print("✅ RENDER COMPLETE")
        print("="*70)
        print(f"\n📹 Final video: {output_path}")
        print(f"\n▶️  Watch it:")
        print(f"   open {output_path}")
        print(f"\n💬 REPORT ISSUES:")
        print(f"   - Text overlapping/cramped?")
        print(f"   - Elements front-loaded (all in first 2s)?")
        print(f"   - Static after initial reveals?")
        print(f"   - Layout feels templated?")
        print(f"   - Wrong colors (should be dark BG, cream text)?")
    else:
        print("\n" + "="*70)
        print("❌ RENDER FAILED")
        print("="*70)
        print(f"\nError: {error}")
        print("\nDebug: Check Remotion setup")


if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)