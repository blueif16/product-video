#!/usr/bin/env python3
"""
重新生成音乐并混合到已渲染的视频

用法:
    python scripts/regenerate_music_and_mux.py <video_project_id>

示例:
    python scripts/regenerate_music_and_mux.py a8beb3c2-01a6-4480-b37f-30fdc56c4e7b
"""
import sys
import os
import json
import subprocess
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def load_env_variable(key: str) -> str:
    """从 .env 文件读取环境变量"""
    # 先尝试系统环境变量
    value = os.getenv(key)
    if value:
        return value

    # 读取 .env 文件
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    env_key, env_value = line.split('=', 1)
                    if env_key.strip() == key:
                        # 移除引号
                        return env_value.strip().strip('"').strip("'")
    return None


def analyze_timeline_for_music_simple(video_project_id: str) -> dict:
    """简化版的时间线分析，直接从 video_spec 读取"""
    spec_path = project_root / "assets" / "specs" / f"{video_project_id}.json"

    with open(spec_path, "r") as f:
        spec = json.load(f)

    meta = spec.get("meta", {})
    clips = spec.get("clips", [])
    fps = meta.get("fps", 30)
    total_frames = meta.get("durationFrames", 0)
    total_duration_s = total_frames / fps

    # 简单的 hit points 提取
    hit_points = []
    for clip in clips:
        start_frame = clip.get("startFrame", 0)
        duration_frames = clip.get("durationFrames", 0)
        start_s = start_frame / fps
        duration_s = duration_frames / fps

        # 提取文本内容
        layers = clip.get("layers", [])
        text_content = ""
        for layer in layers:
            if layer.get("type") == "text":
                text_content = layer.get("content", "")
                break

        # 简单的能量推断
        energy = "medium"
        if start_s == 0 or start_s >= total_duration_s - 2:
            energy = "impact"
        elif duration_s < 1.0:
            energy = "high"

        hit_points.append({
            "time_s": start_s,
            "duration_s": duration_s,
            "energy": energy,
            "description": text_content[:50],
        })

    # 简单的 sections 分组
    sections = []
    section_duration_ms = int(total_duration_s * 1000 / 5)  # 分成5段
    for i in range(5):
        sections.append({
            "name": f"Section {i+1}",
            "duration_ms": section_duration_ms,
            "energy": "medium",
        })

    # 生成基础 composition plan
    composition_plan = {
        "positive_global_styles": ["modern", "electronic", "upbeat", "tech"],
        "negative_global_styles": ["sad", "dark", "aggressive"],
        "sections": [
            {
                "section_name": s["name"],
                "duration_ms": s["duration_ms"],
                "positive_local_styles": ["bright", "clean"],
                "negative_local_styles": ["muddy"],
                "lines": []
            }
            for s in sections
        ]
    }

    # 合并短 sections（ElevenLabs 要求每个 section >= 3000ms）
    MIN_SECTION_DURATION = 3000
    merged_sections = []
    buffer = None

    for section in composition_plan["sections"]:
        if buffer:
            section = {
                "section_name": f"{buffer['section_name']} + {section['section_name']}",
                "duration_ms": buffer["duration_ms"] + section["duration_ms"],
                "positive_local_styles": buffer["positive_local_styles"] + section["positive_local_styles"],
                "negative_local_styles": buffer["negative_local_styles"] + section["negative_local_styles"],
                "lines": []
            }
            buffer = None

        if section["duration_ms"] < MIN_SECTION_DURATION:
            buffer = section
        else:
            merged_sections.append(section)

    if buffer:
        if merged_sections:
            last = merged_sections[-1]
            merged_sections[-1] = {
                "section_name": f"{last['section_name']} + {buffer['section_name']}",
                "duration_ms": last["duration_ms"] + buffer["duration_ms"],
                "positive_local_styles": last["positive_local_styles"] + buffer["positive_local_styles"],
                "negative_local_styles": last["negative_local_styles"] + buffer["negative_local_styles"],
                "lines": []
            }
        else:
            merged_sections.append(buffer)

    composition_plan["sections"] = merged_sections

    return {
        "total_duration_ms": int(total_duration_s * 1000),
        "clip_density": len(clips) / total_duration_s,
        "energy_curve": "medium",
        "recommended_tempo": 115,
        "hit_points": hit_points,
        "sections": sections,
        "composition_plan": composition_plan,
    }


def generate_music_with_elevenlabs(composition_plan: dict, output_path: Path) -> bool:
    """使用 ElevenLabs 生成音乐"""
    try:
        from elevenlabs.client import ElevenLabs

        api_key = load_env_variable("ELEVENLABS_API_KEY")
        if not api_key:
            print("   ❌ 缺少 ELEVENLABS_API_KEY 环境变量")
            return False

        print("   🎹 使用 ElevenLabs 生成音频...")
        client = ElevenLabs(api_key=api_key)

        track = client.music.compose(
            composition_plan=composition_plan,
            respect_sections_durations=True,
        )

        with open(output_path, "wb") as f:
            for chunk in track:
                f.write(chunk)

        print(f"   ✓ 音乐生成成功: {output_path}")
        return True
    except Exception as e:
        print(f"   ❌ 音乐生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def mux_audio_video_ffmpeg(video_path: Path, audio_path: Path, output_path: Path) -> bool:
    """使用 FFmpeg 混合音视频"""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path)
    ]

    try:
        print("   📀 运行 FFmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            print(f"   ✓ 混合成功: {output_path}")
            return True
        else:
            print(f"   ❌ FFmpeg 错误: {result.stderr[:500]}")
            return False
    except Exception as e:
        print(f"   ❌ 混合失败: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("❌ 缺少参数: video_project_id")
        print(f"\n用法: python {sys.argv[0]} <video_project_id>")
        sys.exit(1)

    video_project_id = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"重新生成音乐并混合到视频")
    print(f"{'='*60}")
    print(f"Video Project ID: {video_project_id}\n")

    # 检查文件
    spec_path = project_root / "assets" / "specs" / f"{video_project_id}.json"
    render_path = project_root / "assets" / "renders" / f"{video_project_id}.mp4"

    if not spec_path.exists():
        print(f"❌ VideoSpec 不存在: {spec_path}")
        sys.exit(1)
    if not render_path.exists():
        print(f"❌ 视频文件不存在: {render_path}")
        sys.exit(1)

    print(f"✓ VideoSpec: {spec_path}")
    print(f"✓ 渲染视频: {render_path}")

    # 步骤 1: 分析时间线
    print(f"\n{'='*60}")
    print("步骤 1: 分析视频时间线")
    print(f"{'='*60}")

    try:
        music_analysis = analyze_timeline_for_music_simple(video_project_id)
        print(f"   ✓ 总时长: {music_analysis['total_duration_ms']/1000:.1f}s")
        print(f"   ✓ 片段数: {len(music_analysis['hit_points'])}")
        print(f"   ✓ 音乐段落: {len(music_analysis['sections'])}")
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        sys.exit(1)

    # 步骤 2: 生成音乐
    print(f"\n{'='*60}")
    print("步骤 2: 生成背景音乐")
    print(f"{'='*60}")

    audio_dir = project_root / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{video_project_id}_bgm.mp3"

    if not generate_music_with_elevenlabs(music_analysis["composition_plan"], audio_path):
        sys.exit(1)

    # 步骤 3: 混合音视频
    print(f"\n{'='*60}")
    print("步骤 3: 混合音频和视频")
    print(f"{'='*60}")

    output_path = render_path.parent / f"{render_path.stem}_with_audio{render_path.suffix}"

    if not mux_audio_video_ffmpeg(render_path, audio_path, output_path):
        sys.exit(1)

    print(f"\n{'='*60}")
    print("✅ 完成!")
    print(f"{'='*60}")
    print(f"\n🎬 最终视频 (带音乐): {output_path}\n")


if __name__ == "__main__":
    main()
