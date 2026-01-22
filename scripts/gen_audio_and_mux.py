#!/usr/bin/env python3
"""生成音频并与视频混合"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.music_generator import music_generator_node, mux_audio_video_node

if __name__ == "__main__":
    video_project_id = "67ab3ee1-ab2a-4dec-8f3e-241f957fd8a9"
    render_path = f"/Users/tk/Desktop/productvideo/assets/renders/{video_project_id}.mp4"

    # 生成音频
    print("🎶 生成背景音乐...")
    state = {
        "video_project_id": video_project_id,
        "music_analysis": None,
    }

    # 先加载 music_analysis
    from editor.music_planner import analyze_timeline_for_music
    state["music_analysis"] = analyze_timeline_for_music(video_project_id)

    # 生成音频
    result = music_generator_node(state)
    audio_path = result.get("audio_path")

    if not audio_path:
        print("❌ 音频生成失败")
        sys.exit(1)

    # 混合音视频
    print("\n🎬 混合音视频...")
    mux_state = {
        "render_path": render_path,
        "audio_path": audio_path,
    }

    final_result = mux_audio_video_node(mux_state)
    final_path = final_result.get("final_video_path")

    if final_path:
        print(f"\n✅ 完成！最终视频: {final_path}")
    else:
        print("\n❌ 混合失败")
        sys.exit(1)
