#!/usr/bin/env python3
"""
测试 LLM 是否遵守新的 prompt（不修改 durationMs）
"""
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from tools.music_generator import generate_refined_composition_plan

# 构造测试用的 music_analysis
test_analysis = {
    "total_duration_ms": 10000,
    "clip_density": 1.5,
    "energy_curve": "impact → medium → impact → resolve",
    "recommended_tempo": 120,
    "hit_points": [
        {"time_s": 0.0, "energy": "impact", "description": "Hero moment"},
        {"time_s": 3.0, "energy": "medium", "description": "Feature demo"},
        {"time_s": 6.0, "energy": "impact", "description": "Punch line"},
        {"time_s": 8.5, "energy": "resolve", "description": "CTA"},
    ],
    "sections": [
        {"name": "Hero 1", "duration_ms": 3000, "energy": "impact", "aligned_clips": []},
        {"name": "Feature 2", "duration_ms": 3000, "energy": "medium", "aligned_clips": []},
        {"name": "Hero 3", "duration_ms": 2500, "energy": "impact", "aligned_clips": []},
        {"name": "CTA 4", "duration_ms": 1500, "energy": "resolve", "aligned_clips": []},
    ],
    "composition_plan": {
        "positiveGlobalStyles": ["modern", "tech", "120 BPM"],
        "negativeGlobalStyles": ["slow", "dark", "acoustic"],
        "sections": [
            {
                "sectionName": "Hero 1 (impact)",
                "durationMs": 3000,
                "positiveLocalStyles": ["punchy", "bright"],
                "negativeLocalStyles": ["soft", "ambient"],
                "lines": []
            },
            {
                "sectionName": "Feature 2 (medium)",
                "durationMs": 3000,
                "positiveLocalStyles": ["steady", "melodic"],
                "negativeLocalStyles": ["heavy", "chaotic"],
                "lines": []
            },
            {
                "sectionName": "Hero 3 (impact)",
                "durationMs": 2500,
                "positiveLocalStyles": ["driving", "energetic"],
                "negativeLocalStyles": ["minimal", "sparse"],
                "lines": []
            },
            {
                "sectionName": "CTA 4 (resolve)",
                "durationMs": 1500,
                "positiveLocalStyles": ["resolved", "satisfying"],
                "negativeLocalStyles": ["building", "intense"],
                "lines": []
            },
        ]
    }
}

print("\n" + "="*60)
print("🧪 测试 LLM Prompt 修复")
print("="*60)

print("\n📋 输入的 composition_plan:")
for i, s in enumerate(test_analysis["composition_plan"]["sections"]):
    print(f"   Section {i}: {s['sectionName']} - {s['durationMs']}ms")

print("\n🤖 调用 LLM refinement...")
refined = generate_refined_composition_plan(test_analysis)

print("\n📋 LLM 返回的 composition_plan:")
all_valid = True
for i, s in enumerate(refined["sections"]):
    duration = s["durationMs"]

    if duration < 3000:
        status = "❌ TOO SHORT"
        all_valid = False
    else:
        status = "✓ VALID"

    print(f"   {status} Section {i}: {s['sectionName']} - {duration}ms")

print("\n" + "="*60)
if all_valid:
    print("✅ 测试通过！所有 sections 都满足 >= 3000ms 的要求")
    print(f"   LLM 成功将 {len(test_analysis['composition_plan']['sections'])} 个 sections 处理为 {len(refined['sections'])} 个")
    print("="*60)
    sys.exit(0)
else:
    print("❌ 测试失败！存在 < 3000ms 的 sections")
    print("   LLM 没有正确合并短 sections")
    print("="*60)
    sys.exit(1)
