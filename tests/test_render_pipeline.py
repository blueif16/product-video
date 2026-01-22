#!/usr/bin/env python3
"""
Test Remotion Render Pipeline

Verifies the end-to-end rendering works:
1. Calls Remotion's test-render.ts script
2. Generates a 5-second test video with text animations
3. No assets or database needed - completely standalone

Usage:
    python -m tests.test_render_pipeline

Prerequisites:
    cd remotion && npm install
"""

import subprocess
import os
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def check_remotion_setup() -> tuple[bool, str]:
    """Verify Remotion project is set up correctly."""
    project_root = get_project_root()
    remotion_dir = project_root / "remotion"
    
    # Check directory exists
    if not remotion_dir.exists():
        return False, f"Remotion directory not found at {remotion_dir}"
    
    # Check package.json
    if not (remotion_dir / "package.json").exists():
        return False, "package.json not found in remotion directory"
    
    # Check node_modules
    if not (remotion_dir / "node_modules").exists():
        return False, "node_modules not found. Run 'npm install' in remotion directory"
    
    # Check test script
    if not (remotion_dir / "scripts" / "test-render.ts").exists():
        return False, "test-render.ts script not found"
    
    return True, "Remotion setup verified"


def run_test_render(output_path: str = None) -> tuple[bool, str]:
    """
    Run the Remotion test render.
    
    Args:
        output_path: Optional output path. Defaults to assets/renders/test-render.mp4
    
    Returns:
        (success, message)
    """
    project_root = get_project_root()
    remotion_dir = project_root / "remotion"
    
    # Default output path
    if output_path is None:
        renders_dir = project_root / "assets" / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(renders_dir / "test-render.mp4")
    
    print("\n" + "=" * 60)
    print("🧪 REMOTION RENDER PIPELINE TEST")
    print("=" * 60)
    
    # Check setup
    ok, msg = check_remotion_setup()
    if not ok:
        print(f"\n❌ Setup check failed: {msg}")
        print("\n📋 To fix, run:")
        print(f"   cd {remotion_dir}")
        print("   npm install")
        return False, msg
    
    print(f"\n✓ Remotion setup verified")
    print(f"✓ Output will be: {output_path}")
    
    # Build command
    cmd = [
        "npx",
        "tsx",
        "scripts/test-render.ts",
        output_path,
    ]
    
    print(f"\n🚀 Running: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        # Run the render
        result = subprocess.run(
            cmd,
            cwd=remotion_dir,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode == 0:
            # Verify output file exists
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print("-" * 60)
                print(f"\n✅ TEST PASSED!")
                print(f"   Video rendered: {output_path}")
                print(f"   File size: {size_mb:.2f} MB")
                return True, output_path
            else:
                return False, "Render completed but output file not found"
        else:
            return False, f"Render failed with exit code {result.returncode}"
            
    except subprocess.TimeoutExpired:
        return False, "Render timed out after 5 minutes"
    except FileNotFoundError:
        return False, "npx not found. Ensure Node.js is installed and in PATH."
    except Exception as e:
        return False, str(e)


def main():
    """Main entry point."""
    # Optional: accept custom output path
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    success, result = run_test_render(output_path)
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 PIPELINE TEST COMPLETE")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Open the video to verify it looks correct")
        print("  2. You can now use the full pipeline with real assets")
        print("  3. Run 'remotion studio' in /remotion for live preview")
        print()
        sys.exit(0)
    else:
        print(f"\n❌ Test failed: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
