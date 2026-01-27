#!/usr/bin/env python3
"""
Test script for batch image analysis

Demonstrates:
1. Natural language embedding format "[Type] ([Orientation]): description"
2. User notes passed as context
3. Batch analysis for cross-image relationships
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.image_analyzer import analyze_image, analyze_image_batch


def test_single_with_note():
    """Test single image analysis with user note."""
    print("\n" + "="*80)
    print("TEST 1: Single Image with User Note")
    print("="*80)
    
    # You'd replace this with a real image path
    test_image = "/path/to/test/screenshot.png"
    user_note = "This is our main dashboard showing task metrics"
    
    if not os.path.exists(test_image):
        print(f"⚠️  Test image not found: {test_image}")
        print("Create a test image or update the path")
        return
    
    result = analyze_image(test_image, user_note=user_note)
    
    print(f"\n📋 Result:")
    print(f"   Description: {result['description']}")
    print(f"   Dimensions: {result['width']}×{result['height']}")
    
    # Verify format
    desc = result['description']
    if desc.startswith('[') and ']:' in desc:
        print("✅ Format valid: Natural language embedding detected")
        # Extract type/orientation
        type_orient = desc.split(']:')[0] + ']'
        print(f"   Metadata: {type_orient}")
    else:
        print("⚠️  Format issue: Expected '[Type] ([Orientation]): ...'")


def test_batch_with_notes():
    """Test batch analysis with user notes."""
    print("\n" + "="*80)
    print("TEST 2: Batch Analysis with User Notes")
    print("="*80)
    
    # You'd replace these with real image paths
    test_images = [
        "/path/to/test/login.png",
        "/path/to/test/dashboard.png",
        "/path/to/test/settings.png",
    ]
    
    user_notes = [
        "Login screen - entry point",
        "Main dashboard after login",
        "Settings panel accessed from dashboard menu",
    ]
    
    # Check if files exist
    if not all(os.path.exists(img) for img in test_images):
        print("⚠️  Test images not found")
        print("Update the paths in this script to real images")
        return
    
    results = analyze_image_batch(test_images, user_notes=user_notes)
    
    print(f"\n📋 Results ({len(results)} images):")
    for i, result in enumerate(results, 1):
        print(f"\n   Image {i}: {os.path.basename(result['path'])}")
        print(f"   Description: {result['description'][:100]}...")
        print(f"   Dimensions: {result['width']}×{result['height']}")
        
        # Check for relationship mentions
        if i > 1:
            desc_lower = result['description'].lower()
            if any(word in desc_lower for word in ['previous', 'after', 'from', 'accessed']):
                print(f"   ✅ Cross-reference detected!")


def test_batch_without_notes():
    """Test batch analysis without user notes (pure AI vision)."""
    print("\n" + "="*80)
    print("TEST 3: Batch Analysis without User Notes")
    print("="*80)
    
    test_images = [
        "/path/to/test/screen1.png",
        "/path/to/test/screen2.png",
    ]
    
    if not all(os.path.exists(img) for img in test_images):
        print("⚠️  Test images not found")
        return
    
    results = analyze_image_batch(test_images)  # No user_notes
    
    print(f"\n📋 Results (pure AI analysis):")
    for i, result in enumerate(results, 1):
        print(f"\n   Image {i}:")
        print(f"   {result['description']}")


def show_format_examples():
    """Show expected output formats."""
    print("\n" + "="*80)
    print("EXPECTED OUTPUT FORMATS")
    print("="*80)
    
    examples = [
        "Phone screenshot (portrait): Login screen with email and password fields, clean white background, blue (#2563EB) call-to-action button at bottom [1170×2532]",
        "Website screenshot (landscape): Landing page featuring hero section with product image, gradient background purple to blue, centered content layout, navigation bar at top [1920×1080]",
        "Decorative image (square): Abstract geometric pattern with overlapping circles, vibrant color palette of orange (#FF6B35), teal (#00B8A9), minimal style [1080×1080]",
        "Phone screenshot (portrait): Dashboard (accessed from previous login screen) showing task list with completion checkboxes, progress bar at 65%, purple theme (#7C3AED) [1170×2532]",
    ]
    
    print("\n✅ Valid formats:")
    for ex in examples:
        # Extract metadata
        type_orient = ex.split(']:')[0] + ']'
        print(f"\n   {type_orient}")
        print(f"   → {ex}")


if __name__ == "__main__":
    print("\n🧪 StreamLine Image Analyzer Test Suite")
    
    # Show expected formats first
    show_format_examples()
    
    # Run tests (update paths first!)
    # test_single_with_note()
    # test_batch_with_notes()
    # test_batch_without_notes()
    
    print("\n" + "="*80)
    print("💡 To run actual tests:")
    print("   1. Update image paths in this file")
    print("   2. Uncomment the test functions")
    print("   3. Run: python src/tools/test_image_analyzer.py")
    print("="*80 + "\n")
