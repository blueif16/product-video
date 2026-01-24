#!/usr/bin/env python3
"""
Migration Script: V1 → V2

Safely switches between old and new implementations.
"""
import shutil
import os
from pathlib import Path

BASE_DIR = Path("/Users/tk/Desktop/productvideo")
SRC_EDITOR_DIR = BASE_DIR / "src" / "editor"
V1_DIR = SRC_EDITOR_DIR / "v1"
V2_DIR = SRC_EDITOR_DIR / "v2"

FILES = ["planner.py", "clip_composer.py", "graph.py"]


def install_v2():
    """Install V2 files from v2/ to active location."""
    print("\n🚀 Installing V2 files...")

    for filename in FILES:
        v2_path = V2_DIR / filename
        target_path = SRC_EDITOR_DIR / filename

        if v2_path.exists():
            shutil.copy2(v2_path, target_path)
            print(f"   ✓ Installed v2/{filename} → {filename}")
        else:
            print(f"   ❌ v2/{filename} not found")


def restore_v1():
    """Restore V1 files from v1/ to active location."""
    print("\n♻️  Restoring V1 files...")

    for filename in FILES:
        v1_path = V1_DIR / filename
        target_path = SRC_EDITOR_DIR / filename

        if v1_path.exists():
            shutil.copy2(v1_path, target_path)
            print(f"   ✓ Restored v1/{filename} → {filename}")
        else:
            print(f"   ⚠️  v1/{filename} not found")


def check_status():
    """Check which version is currently active."""
    print("\n📊 Current Status:")

    for filename in FILES:
        target_path = SRC_EDITOR_DIR / filename
        v1_path = V1_DIR / filename
        v2_path = V2_DIR / filename

        if target_path.exists():
            with open(target_path, 'r') as f:
                content = ''.join(f.readlines()[:10])
                version = "V2" if "V2" in content or "FIXES:" in content else "V1"

            v1_exists = "✓" if v1_path.exists() else "✗"
            v2_exists = "✓" if v2_path.exists() else "✗"
            print(f"   {filename}: {version} (v1: {v1_exists}, v2: {v2_exists})")
        else:
            print(f"   {filename}: NOT FOUND")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("""
Usage:
    python migrate.py install     # Install V2 (backs up V1)
    python migrate.py restore     # Restore V1 from backup
    python migrate.py status      # Check current version
        """)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "install":
        install_v2()
        print("\n✅ V2 installed! Run your editor to test.")

    elif command == "restore":
        restore_v1()
        print("\n✅ V1 restored!")
        
    elif command == "status":
        check_status()
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
