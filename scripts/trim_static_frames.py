"""
视频静态帧裁剪工具

自动检测视频中的运动片段，移除静态等待部分。
使用 OpenCV Frame Difference + FFmpeg 快速切割。

用法:
    python scripts/trim_static_frames.py input.mp4
    python scripts/trim_static_frames.py input.mp4 -o output.mp4
    python scripts/trim_static_frames.py input.mp4 --threshold 8.0
"""
import cv2
import numpy as np
import subprocess
import tempfile
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def log(message: str) -> None:
    """打印日志"""
    print(message, flush=True)


def adaptive_threshold(video_path: str, percentile: float = 75) -> float:
    """
    根据视频整体差异分布自动确定阈值

    Args:
        video_path: 视频路径
        percentile: 百分位数（建议 70-80）

    Returns:
        自适应阈值
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    diffs = []
    prev_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, gray)
            diffs.append(np.mean(diff))

        prev_frame = gray

    cap.release()

    if not diffs:
        return 5.0

    threshold = np.percentile(diffs, percentile)
    return max(threshold, 3.0)


def detect_motion_segments(
    video_path: str,
    threshold: float,
    min_motion_duration: float = 0.3
) -> Tuple[List[Tuple[float, float]], float]:
    """
    检测视频中的运动片段

    Args:
        video_path: 视频路径
        threshold: 帧差异阈值（0-255）
        min_motion_duration: 最小运动时长（秒）

    Returns:
        (segments, fps) - 运动片段时间戳列表和帧率
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    prev_frame = None
    motion_flags = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, gray)
            mean_diff = np.mean(diff)
            motion_flags.append(mean_diff > threshold)

        prev_frame = gray

    cap.release()

    # 合并连续运动帧为时间段
    segments = []
    in_motion = False
    start_frame = 0
    min_frames = int(min_motion_duration * fps)

    for i, is_motion in enumerate(motion_flags):
        if is_motion and not in_motion:
            start_frame = i
            in_motion = True
        elif not is_motion and in_motion:
            if i - start_frame >= min_frames:
                segments.append((start_frame / fps, i / fps))
            in_motion = False

    if in_motion and len(motion_flags) - start_frame >= min_frames:
        segments.append((start_frame / fps, len(motion_flags) / fps))

    return segments, fps


def merge_segments(segments: List[Tuple[float, float]], max_gap: float = 0.3) -> List[Tuple[float, float]]:
    """
    合并间隔小于 max_gap 秒的片段

    Args:
        segments: 时间段列表 [(start, end), ...]
        max_gap: 最大间隔（秒）

    Returns:
        合并后的时间段列表
    """
    if not segments:
        return []

    merged = [segments[0]]
    for start, end in segments[1:]:
        last_start, last_end = merged[-1]
        if start - last_end <= max_gap:
            merged[-1] = (last_start, end)
        else:
            merged.append((start, end))

    return merged


def add_buffer(
    segments: List[Tuple[float, float]],
    buffer: float = 0.2,
    video_duration: Optional[float] = None
) -> List[Tuple[float, float]]:
    """
    在运动片段前后各加 buffer 秒

    Args:
        segments: 时间段列表
        buffer: 缓冲时间（秒）
        video_duration: 视频总时长（秒）

    Returns:
        添加缓冲后的时间段列表
    """
    buffered = []
    for start, end in segments:
        new_start = max(0, start - buffer)
        new_end = end + buffer
        if video_duration:
            new_end = min(video_duration, new_end)
        buffered.append((new_start, new_end))

    return buffered


def extract_segments(
    video_path: str,
    segments: List[Tuple[float, float]],
    output_path: str
) -> None:
    """
    使用 FFmpeg 提取运动片段并拼接

    Args:
        video_path: 输入视频路径
        segments: 时间段列表
        output_path: 输出视频路径
    """
    if not segments:
        raise ValueError("没有检测到运动片段")

    if len(segments) == 1:
        start, end = segments[0]
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(start), "-to", str(end),
            "-c", "copy",
            output_path
        ], check=True, capture_output=True)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        segment_paths = []
        concat_file = os.path.join(tmpdir, "segments.txt")

        for i, (start, end) in enumerate(segments):
            segment_path = os.path.join(tmpdir, f"segment_{i}.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path,
                "-ss", str(start), "-to", str(end),
                "-c", "copy",
                segment_path
            ], check=True, capture_output=True)
            segment_paths.append(segment_path)

        with open(concat_file, "w") as f:
            for path in segment_paths:
                f.write(f"file '{path}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path
        ], check=True, capture_output=True)


def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    return frame_count / fps if fps > 0 else 0


def trim_video(
    input_path: str,
    output_path: Optional[str] = None,
    threshold: Optional[float] = None,
    min_motion_duration: float = 0.3,
    merge_gap: float = 0.3,
    buffer: float = 0.2,
    verbose: bool = True
) -> str:
    """
    自动裁剪视频中的静态帧，只保留运动片段

    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径（None = 自动生成 .trimmed.mp4）
        threshold: 帧差异阈值（None = 自动检测）
        min_motion_duration: 最小运动时长（秒）
        merge_gap: 合并间隔（秒）
        buffer: 缓冲时间（秒）
        verbose: 是否打印详细日志

    Returns:
        裁剪后的视频路径（如果无需裁剪则返回原路径）
    """
    input_path = str(Path(input_path).resolve())

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"视频文件不存在: {input_path}")

    if output_path is None:
        output_path = str(Path(input_path).with_suffix('')) + '.trimmed.mp4'

    if verbose:
        log(f"🎬 裁剪视频静态帧: {Path(input_path).name}")

    # 1. 获取视频时长
    duration = get_video_duration(input_path)

    # 2. 自动检测阈值
    if threshold is None:
        threshold = adaptive_threshold(input_path)
        if verbose:
            log(f"   自动阈值: {threshold:.2f}")

    # 3. 检测运动片段
    segments, _ = detect_motion_segments(input_path, threshold, min_motion_duration)

    if not segments:
        if verbose:
            log(f"   ⚠️  未检测到运动片段，保留原视频")
        return input_path

    # 4. 合并相邻片段
    segments = merge_segments(segments, merge_gap)

    # 5. 添加缓冲
    segments = add_buffer(segments, buffer, duration)

    # 6. 检查是否需要裁剪
    total_motion = sum(end - start for start, end in segments)
    coverage = total_motion / duration if duration > 0 else 0

    if coverage >= 0.95:
        if verbose:
            log(f"   ℹ️  视频大部分是运动 ({coverage*100:.1f}%)，跳过裁剪")
        return input_path

    # 7. 打印片段信息
    if verbose:
        log(f"   检测到 {len(segments)} 个运动片段:")
        for i, (start, end) in enumerate(segments, 1):
            log(f"     片段 {i}: {start:.2f}s - {end:.2f}s ({end-start:.2f}s)")

        reduction = (1 - total_motion / duration) * 100 if duration > 0 else 0
        log(f"   原始: {duration:.1f}s → 裁剪后: {total_motion:.1f}s (减少 {reduction:.0f}%)")

    # 8. 提取并拼接
    try:
        extract_segments(input_path, segments, output_path)
        if verbose:
            log(f"   ✓ 保存至: {Path(output_path).name}")
        return output_path
    except subprocess.CalledProcessError as e:
        if verbose:
            log(f"   ❌ FFmpeg 错误: {e.stderr.decode() if e.stderr else str(e)}")
        raise
    except Exception as e:
        if verbose:
            log(f"   ❌ 裁剪失败: {str(e)}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="自动裁剪视频中的静态帧，只保留运动片段",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s video.mp4                          # 自动裁剪，输出 video.trimmed.mp4
  %(prog)s video.mp4 -o output.mp4            # 指定输出路径
  %(prog)s video.mp4 --threshold 8.0          # 手动设置阈值
  %(prog)s video.mp4 --buffer 0.5             # 增加缓冲时间
  %(prog)s video.mp4 --quiet                  # 静默模式
        """
    )

    parser.add_argument(
        "input",
        help="输入视频路径"
    )
    parser.add_argument(
        "-o", "--output",
        help="输出视频路径（默认: input.trimmed.mp4）"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="帧差异阈值 0-255（默认: 自动检测）"
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=0.3,
        help="最小运动时长（秒，默认: 0.3）"
    )
    parser.add_argument(
        "--merge-gap",
        type=float,
        default=0.3,
        help="合并间隔（秒，默认: 0.3）"
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=0.2,
        help="缓冲时间（秒，默认: 0.2）"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式（不打印日志）"
    )

    args = parser.parse_args()

    try:
        output = trim_video(
            input_path=args.input,
            output_path=args.output,
            threshold=args.threshold,
            min_motion_duration=args.min_duration,
            merge_gap=args.merge_gap,
            buffer=args.buffer,
            verbose=not args.quiet
        )

        if not args.quiet:
            print(f"\n✅ 完成: {output}")

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"\n❌ 文件不存在: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ 参数错误: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ FFmpeg 错误: {e.stderr.decode() if e.stderr else str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未知错误: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

