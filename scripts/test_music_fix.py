#!/usr/bin/env python3
"""
测试音乐生成修复

功能：
1. 从现有的 video_project_id 生成 composition_plan
2. 验证所有 sections 的 duration_ms >= 3000ms
3. 生成音乐
4. 将音乐与视频混合
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from editor.music_planner import analyze_timeline_for_music
from tools.music_generator import MusicGenerator
import subprocess
import json

VIDEO_PROJECT_ID = "f766c5a6-e77f-4b29-b637-a9479ee463ec"
VIDEO_PATH = project_root / "assets/renders" / f"{VIDEO_PROJECT_ID}.mp4"
AUDIO_OUTPUT = project_root / "assets/audio" / f"{VIDEO_PROJECT_ID}_bgm_test.mp3"
FINAL_OUTPUT = project_root / "assets/renders" / f"{VIDEO_PROJECT_ID}_with_music.mp4"


def main():
    print("\n" + "="*60)
    print("🎵 测试音乐生成修复")
    print("="*60)

    # 1. 分析时间线并生成 composition_plan
    print("\n📊 步骤 1: 分析视频时间线...")
    try:
        analysis = analyze_timeline_for_music(VIDEO_PROJECT_ID)
        print(f"   ✓ 分析完成")
        print(f"   - 总时长: {analysis['total_duration_ms'] / 1000:.1f}s")
        print(f"   - 推荐节奏: {analysis['recommended_tempo']} BPM")
        print(f"   - 能量曲线: {analysis['energy_curve']}")
    except Exception as e:
        print(f"   ❌ 分析失败: {e}")
        return 1

    # 2. 验证 composition_plan
    print("\n✅ 步骤 2: 验证 composition_plan...")
    composition_plan = analysis["composition_plan"]
    sections = composition_plan.get("sections", [])

    print(f"   - 总共 {len(sections)} 个 sections:")
    all_valid = True
    for i, section in enumerate(sections, 1):
        duration_ms = section.get("durationMs", 0)
        name = section.get("sectionName", "Unknown")
        status = "✓" if duration_ms >= 3000 else "✗"
        print(f"     {status} Section {i}: {name} ({duration_ms}ms)")
        if duration_ms < 3000:
            all_valid = False

    if not all_valid:
        print("\n   ❌ 验证失败: 存在 duration < 3000ms 的 sections")
        print("   修复逻辑可能仍有问题，请检查 music_planner.py")
        return 1

    print("\n   ✓ 所有 sections 都满足 >= 3000ms 的要求")

    # 3. 生成音乐
    print("\n🎹 步骤 3: 生成音乐...")
    AUDIO_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        generator = MusicGenerator()
        result = generator.generate_from_composition_plan(
            composition_plan=composition_plan,
            output_path=AUDIO_OUTPUT,
            respect_durations=True,
        )
        print(f"   ✓ 音乐生成成功: {result.output_path}")
        print(f"   - 时长: {result.duration_ms / 1000:.1f}s")
        print(f"   - Sections: {', '.join(result.sections or [])}")
    except Exception as e:
        print(f"   ❌ 音乐生成失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 4. 混合音频和视频
    print("\n🎬 步骤 4: 混合音频和视频...")

    if not VIDEO_PATH.exists():
        print(f"   ❌ 视频文件不存在: {VIDEO_PATH}")
        return 1

    if not AUDIO_OUTPUT.exists():
        print(f"   ❌ 音频文件不存在: {AUDIO_OUTPUT}")
        return 1

    cmd = [
        "ffmpeg", "-y",
        "-i", str(VIDEO_PATH),
        "-i", str(AUDIO_OUTPUT),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(FINAL_OUTPUT)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            print(f"   ✓ 混合成功: {FINAL_OUTPUT}")
            print(f"\n{'='*60}")
            print("✅ 测试完成！所有步骤都成功")
            print(f"{'='*60}")
            print(f"\n最终视频: {FINAL_OUTPUT}")
            return 0
        else:
            print(f"   ❌ FFmpeg 错误: {result.stderr[:500]}")
            return 1

    except subprocess.TimeoutExpired:
        print("   ❌ FFmpeg 超时")
        return 1
    except FileNotFoundError:
        print("   ❌ FFmpeg 未安装，请运行: brew install ffmpeg")
        return 1
    except Exception as e:
        print(f"   ❌ 混合失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
