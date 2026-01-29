#!/usr/bin/env python3
"""
Test: Reproduce Clip 4 Mesh Overlay Issue

Tests if validation catches oversized mesh points on light background.
Uses EXACT composerNotes from the problematic clip.

Usage:
    cd /Users/tk/Desktop/productvideo/src
    python test_overlay_validation.py
"""
import json
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.draft_tools import run_measure_script, format_validation_report, SAFE_ZONE

# EXACT problematic layers from clip 4 "Interactive Insights"
PROBLEMATIC_LAYERS = [
    {
        "type": "background",
        "color": "#F8FAFC",
        "zIndex": 0
    },
    {
        "mesh": True,
        "type": "background",
        "zIndex": 1,
        "meshPoints": [
            {
                "x": 80,
                "y": 20,
                "blur": 100,
                "size": 400,  # 37% of canvas - WAY TOO BIG
                "color": "#008DFF"
            },
            {
                "x": 10,
                "y": 80,
                "blur": 120,
                "size": 300,  # 28% of canvas - TOO BIG
                "color": "#008DFF"
            }
        ],
        "meshAnimate": True
    },
    {
        "src": "https://example.com/screenshot.png",
        "type": "image",
        "scale": 0.75,
        "device": "iphone",
        "zIndex": 2,
        "position": {
            "x": 72.5,
            "y": 50,
            "anchor": "center"
        },
        "animation": {
            "feel": "kinetic",
            "enter": "slide_left",
            "enterDuration": 15
        },
        "startFrame": 5,
        "durationFrames": 85
    },
    {
        "type": "text",
        "style": {
            "color": "#008DFF",
            "fontSize": 24,
            "textAlign": "left",
            "fontWeight": 600,
            "letterSpacing": 2
        },
        "zIndex": 3,
        "content": "CHAT",
        "position": {
            "x": 12,
            "y": 32,
            "anchor": "top-left"
        },
        "animation": {
            "feel": "snappy",
            "enter": "fade",
            "enterDuration": 10
        },
        "startFrame": 15,
        "durationFrames": 75
    },
    {
        "type": "text",
        "style": {
            "color": "#111827",
            "fontSize": 72,
            "maxWidth": 600,
            "textAlign": "left",
            "fontWeight": 700,
            "lineHeight": 1.1
        },
        "zIndex": 4,
        "content": "Interactive Insights",
        "position": {
            "x": 12,
            "y": 38,
            "anchor": "top-left"
        },
        "animation": {
            "feel": "kinetic",
            "enter": "stagger",
            "enterDuration": 15
        },
        "startFrame": 22,
        "durationFrames": 68
    },
    {
        "type": "text",
        "style": {
            "color": "#374151",
            "fontSize": 36,
            "maxWidth": 550,
            "textAlign": "left",
            "fontWeight": 500,
            "lineHeight": 1.4
        },
        "zIndex": 5,
        "content": "Chat with your AI guide to navigate your day with clarity.",
        "position": {
            "x": 12,
            "y": 58,
            "anchor": "top-left"
        },
        "animation": {
            "feel": "kinetic",
            "enter": "slide_up",
            "enterDuration": 15
        },
        "startFrame": 30,
        "durationFrames": 60
    }
]

# Also test the orb issue from clip 1
PROBLEMATIC_ORBS = [
    {
        "type": "background",
        "color": "#F8FAFC",
        "zIndex": 0
    },
    {
        "orbs": True,
        "type": "background",
        "zIndex": 1,
        "orbBlur": 80,
        "orbCount": 4,
        "orbColors": ["#008DFF"],
        "orbOpacity": 0.1,
        "orbPositions": [
            {"x": 15, "y": 20},
            {"x": 85, "y": 25},
            {"x": 20, "y": 80},
            {"x": 80, "y": 85}
        ],
        "orbSizeRange": [300, 500],  # 28-46% of canvas - WAY TOO BIG
        "orbDriftSpeed": 3
    },
    {
        "type": "text",
        "style": {
            "color": "#111827",
            "fontSize": 88,
            "textAlign": "center",
            "fontFamily": "Inter",
            "fontWeight": 800
        },
        "zIndex": 2,
        "content": "Your Future, Refined.",
        "position": {
            "x": 50,
            "y": 42,
            "anchor": "center"
        },
        "startFrame": 10,
        "durationFrames": 80
    }
]


def test_validation(name: str, layers: list):
    """Run validation and print results."""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    
    # Run measurement script
    results = run_measure_script(layers)
    
    if results.get('error'):
        print(f"⚠️  Measurement error: {results['error']}")
        print("Using fallback...")
    
    # Format report
    report = format_validation_report(results)
    print(report)
    
    # Check for overlay issues specifically
    overlay_issues = [i for i in results.get('issues', []) 
                      if i.get('type') in ('overlay_too_large', 'overlay_too_opaque')]
    
    if overlay_issues:
        print(f"\n✅ VALIDATION CAUGHT OVERLAY ISSUES:")
        for issue in overlay_issues:
            print(f"   - {issue.get('type')}: {issue.get('message', '')}")
    else:
        print(f"\n❌ VALIDATION MISSED OVERLAY ISSUES - needs debugging")
    
    return results


def main():
    print("\n" + "="*70)
    print("OVERLAY VALIDATION TEST")
    print("Reproducing exact problematic clips from video log")
    print("="*70)
    
    # Test 1: Mesh issue (clip 4)
    mesh_results = test_validation("Clip 4 - Oversized Mesh Points", PROBLEMATIC_LAYERS)
    
    # Test 2: Orb issue (clip 1)
    orb_results = test_validation("Clip 1 - Oversized Orbs", PROBLEMATIC_ORBS)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    mesh_caught = any(i.get('type') == 'overlay_too_large' 
                      for i in mesh_results.get('issues', []))
    orb_caught = any(i.get('type') in ('overlay_too_large', 'overlay_too_opaque')
                     for i in orb_results.get('issues', []))
    
    print(f"Mesh overlay issue caught: {'✅ YES' if mesh_caught else '❌ NO'}")
    print(f"Orb overlay issue caught:  {'✅ YES' if orb_caught else '❌ NO'}")
    
    if mesh_caught and orb_caught:
        print("\n✅ All overlay validations working!")
    else:
        print("\n❌ Some validations not working - check measure-layers.js")


if __name__ == "__main__":
    main()
