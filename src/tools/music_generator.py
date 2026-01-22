"""
ElevenLabs Music Generation Service

Two generation modes:
1. Simple prompt - for quick/generic BGM
2. Composition plan - for precisely aligned music

The composition plan mode aligns musical sections to visual beats,
ensuring the music "breathes" with the video.
"""
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
import os
import subprocess
import re

from elevenlabs.client import ElevenLabs
from config import Config


def _camel_to_snake(name: str) -> str:
    """将 camelCase 转换为 snake_case"""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def _convert_dict_keys_to_snake(data: Any) -> Any:
    """递归转换字典键从 camelCase 到 snake_case"""
    if isinstance(data, dict):
        return {_camel_to_snake(k): _convert_dict_keys_to_snake(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_dict_keys_to_snake(item) for item in data]
    else:
        return data


@dataclass
class GenerationResult:
    """Result of music generation."""
    output_path: Path
    duration_ms: int
    mode: str  # "prompt" or "composition_plan"
    tempo: Optional[int] = None
    sections: Optional[List[str]] = None


class MusicGenerator:
    """ElevenLabs music generator with composition plan support."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.ELEVENLABS_API_KEY
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable required")
        self.client = ElevenLabs(api_key=self.api_key)

    def generate_from_prompt(
        self,
        prompt: str,
        duration_seconds: int = 60,
        output_path: Optional[Path] = None,
        force_instrumental: bool = True,
    ) -> GenerationResult:
        """
        Generate music from a simple text prompt.
        
        Best for: Quick generation, generic BGM, testing.
        """
        if not output_path:
            output_path = Path("bgm.mp3")

        track = self.client.music.compose(
            prompt=prompt,
            music_length_ms=duration_seconds * 1000,
            force_instrumental=force_instrumental,
        )

        with open(output_path, "wb") as f:
            for chunk in track:
                f.write(chunk)

        return GenerationResult(
            output_path=output_path,
            duration_ms=duration_seconds * 1000,
            mode="prompt",
        )

    def generate_from_composition_plan(
        self,
        composition_plan: Dict[str, Any],
        output_path: Optional[Path] = None,
        respect_durations: bool = True,
    ) -> GenerationResult:
        """
        Generate music from a structured composition plan.

        Best for: Precise alignment with video beats.

        The composition plan should have:
        - positiveGlobalStyles: list[str]
        - negativeGlobalStyles: list[str]
        - sections: list[{sectionName, durationMs, positiveLocalStyles, negativeLocalStyles, lines}]
        """
        if not output_path:
            output_path = Path("bgm_aligned.mp3")

        # 转换 camelCase 到 snake_case（ElevenLabs API 要求）
        api_plan = _convert_dict_keys_to_snake(composition_plan)

        # 保存参数到文件（用于调试和重新生成）
        plan_file = output_path.parent / f"{output_path.stem}_plan.json"
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(api_plan, f, indent=2, ensure_ascii=False)
        print(f"   💾 Composition plan saved: {plan_file}")

        track = self.client.music.compose(
            composition_plan=api_plan,
            respect_sections_durations=respect_durations,
        )

        with open(output_path, "wb") as f:
            for chunk in track:
                f.write(chunk)

        # 从转换后的 plan 读取数据
        total_ms = sum(s.get("duration_ms", 0) for s in api_plan.get("sections", []))
        section_names = [s.get("section_name", "?") for s in api_plan.get("sections", [])]

        return GenerationResult(
            output_path=output_path,
            duration_ms=total_ms,
            mode="composition_plan",
            sections=section_names,
        )

    def generate_aligned_bgm(
        self,
        video_project_id: str,
        output_path: Optional[Path] = None,
    ) -> GenerationResult:
        """
        Generate BGM aligned to the video's visual beats.
        
        This is the main entry point for StreamLine integration.
        
        1. Loads the music analysis from the database
        2. Uses the composition plan for precise alignment
        3. Returns the generated audio path
        """
        from editor.music_planner import analyze_timeline_for_music
        
        # Analyze the video timeline
        analysis = analyze_timeline_for_music(video_project_id)
        
        if not output_path:
            output_path = Path(f"assets/audio/{video_project_id}_bgm.mp3")
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate using composition plan
        result = self.generate_from_composition_plan(
            composition_plan=analysis["composition_plan"],
            output_path=output_path,
            respect_durations=True,
        )
        
        result.tempo = analysis["recommended_tempo"]
        
        return result


# ─────────────────────────────────────────────────────────────
# LLM-Enhanced Composition Plan Generation
# ─────────────────────────────────────────────────────────────

def generate_refined_composition_plan(
    music_analysis: dict,
    user_preferences: Optional[str] = None,
) -> dict:
    """
    Use LLM to refine the composition plan based on context.
    
    The base composition plan from music_planner is good, but an LLM
    can make it more creative and contextually appropriate.
    
    Args:
        music_analysis: Output from analyze_timeline_for_music()
        user_preferences: Optional user input about music style
    
    Returns:
        Refined composition_plan dict
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    
    model = ChatGoogleGenerativeAI(
        model=Config.MODEL_NAME,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.4,
    )
    
    # Build context for LLM
    hit_points_summary = "\n".join([
        f"  {hp['time_s']:.1f}s: {hp['energy']} - {hp['description']}"
        for hp in music_analysis['hit_points'][:15]  # First 15 for context
    ])
    
    sections_summary = "\n".join([
        f"  {s['name']} ({s['duration_ms']/1000:.1f}s) - {s['energy']}"
        for s in music_analysis['sections']
    ])
    
    base_plan = music_analysis['composition_plan']
    
    prompt = f"""You are a music director for Product Hunt videos. Refine this composition plan.

## VIDEO CONTEXT

Total Duration: {music_analysis['total_duration_ms'] / 1000:.1f}s
Clip Density: {music_analysis['clip_density']:.2f} clips/second
Energy Curve: {music_analysis['energy_curve']}
Recommended Tempo: {music_analysis['recommended_tempo']} BPM

## HIT POINTS (Visual Beats)
{hit_points_summary}

## PROPOSED SECTIONS
{sections_summary}

## USER PREFERENCE
{user_preferences or "No specific preference - use Product Hunt style"}

## CURRENT PLAN
```json
{json.dumps(base_plan, indent=2)}
```

## YOUR TASK

Refine the composition plan to make the music more:
1. **Aligned** - Musical transitions should hit at visual beat boundaries
2. **Appropriate** - Match the energy curve of the video
3. **Professional** - Product Hunt quality, modern tech aesthetic

CRITICAL API CONSTRAINT - Section Duration Requirements:
- ElevenLabs API requires ALL sections to have durationMs >= 3000
- The input plan may contain sections with durationMs < 3000
- You MUST merge adjacent sections if their durationMs < 3000
- When merging sections:
  * Combine sectionNames with " + " separator (e.g., "Intro + Build")
  * Concatenate positiveLocalStyles and negativeLocalStyles arrays
  * Sum up the durationMs values
  * Keep the lines array (usually empty for instrumental)
- After processing, verify ALL sections have durationMs >= 3000
- If you output any section with durationMs < 3000, the API will return 422 error

Rules for composition:
- You have full freedom to adjust section structure and durations as needed
- Refine positiveLocalStyles and negativeLocalStyles for musical quality
- You can adjust positiveGlobalStyles/negativeGlobalStyles
- Each section should have 3-5 styles (not more)
- Be specific: "punchy side-chain kick" > "drums"

Return ONLY the refined JSON composition plan, no explanation.
The plan must have this exact structure:
{{
  "positiveGlobalStyles": [...],
  "negativeGlobalStyles": [...],
  "sections": [
    {{
      "sectionName": "...",
      "durationMs": <exact number>,
      "positiveLocalStyles": [...],
      "negativeLocalStyles": [...],
      "lines": []
    }},
    ...
  ]
}}
"""

    response = model.invoke([HumanMessage(content=prompt)])

    # Parse the JSON response
    try:
        # Extract JSON from response (might have markdown code blocks)
        # Handle both string and list responses from LangChain
        response_content = response.content
        if isinstance(response_content, list):
            # Extract text from list of content blocks
            response_text = ""
            for block in response_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    response_text += block.get("text", "")
                elif isinstance(block, str):
                    response_text += block
        else:
            response_text = response_content
        
        # Remove markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        refined_plan = json.loads(response_text.strip())
        
        # Validate structure
        if "sections" not in refined_plan or not refined_plan["sections"]:
            print("   ⚠️  Invalid plan structure, using base plan")
            return base_plan
        
        return refined_plan
        
    except json.JSONDecodeError as e:
        print(f"   ⚠️  Failed to parse LLM response: {e}")
        print(f"   Using base composition plan")
        return base_plan


# ─────────────────────────────────────────────────────────────
# LangGraph Nodes
# ─────────────────────────────────────────────────────────────

def music_generator_node(state: dict) -> dict:
    """
    LangGraph node: Generate aligned BGM for the video.
    
    Uses the composition plan from music_planner_node.
    Optionally refines the plan with LLM.
    """
    print("\n🎶 Generating background music...")
    
    video_project_id = state["video_project_id"]
    music_analysis = state.get("music_analysis")
    
    if not music_analysis:
        print("   ❌ No music analysis found. Run music_planner first.")
        return {"audio_path": None}
    
    try:
        # Optionally refine the composition plan with LLM
        user_input = state.get("user_input", "")
        
        print("   📝 Refining composition plan with LLM...")
        refined_plan = generate_refined_composition_plan(
            music_analysis,
            user_preferences=user_input,
        )
        
        # Log the refined sections
        print(f"   ✓ Refined plan has {len(refined_plan.get('sections', []))} sections")
        
        # Generate the music
        print("   🎹 Generating audio with ElevenLabs...")
        generator = MusicGenerator()
        
        output_path = Path(f"assets/audio/{video_project_id}_bgm.mp3")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = generator.generate_from_composition_plan(
            composition_plan=refined_plan,
            output_path=output_path,
            respect_durations=True,
        )
        
        print(f"\n   ✓ Music generated: {result.output_path}")
        print(f"     Duration: {result.duration_ms / 1000:.1f}s")
        print(f"     Sections: {', '.join(result.sections or [])}")
        
        return {
            "audio_path": str(result.output_path),
            "refined_composition_plan": refined_plan,
        }
        
    except Exception as e:
        print(f"\n   ❌ Music generation failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "audio_path": None,
            "render_error": str(e),
        }


def mux_audio_video_node(state: dict) -> dict:
    """
    LangGraph node: Combine rendered video with generated audio.
    
    Uses FFmpeg to mux:
    - video from render_path (video without audio)
    - audio from audio_path (generated BGM)
    
    Output: final_video_path (video with audio)
    """
    print("\n🎬 Muxing audio with video...")
    
    render_path = state.get("render_path")
    audio_path = state.get("audio_path")
    
    if not render_path:
        print("   ⚠️  No render_path found, skipping mux")
        return {}
    
    if not audio_path:
        print("   ⚠️  No audio_path found, skipping mux")
        return {"final_video_path": render_path}
    
    if not os.path.exists(render_path):
        print(f"   ⚠️  Video file not found: {render_path}")
        return {}
    
    if not os.path.exists(audio_path):
        print(f"   ⚠️  Audio file not found: {audio_path}")
        return {"final_video_path": render_path}
    
    # Output path: video_with_audio.mp4
    video_path = Path(render_path)
    output_path = video_path.parent / f"{video_path.stem}_with_audio{video_path.suffix}"
    
    # FFmpeg command: add audio to video
    # -shortest: end when shortest stream ends (in case audio is slightly longer)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(render_path),      # Video input
        "-i", str(audio_path),       # Audio input
        "-map", "0:v:0",             # Use video stream from input 0
        "-map", "1:a:0",             # Use audio stream from input 1
        "-c:v", "copy",              # Copy video stream (no re-encode)
        "-c:a", "aac",               # Encode audio as AAC
        "-b:a", "192k",              # Audio bitrate
        "-shortest",                 # End when shortest stream ends
        str(output_path)
    ]
    
    try:
        print(f"   📀 Running FFmpeg...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode == 0:
            print(f"   ✓ Final video: {output_path}")
            return {
                "final_video_path": str(output_path),
            }
        else:
            print(f"   ❌ FFmpeg error: {result.stderr[:500]}")
            # Return original video path as fallback
            return {
                "final_video_path": render_path,
                "mux_error": result.stderr,
            }
            
    except subprocess.TimeoutExpired:
        print("   ❌ FFmpeg timed out")
        return {
            "final_video_path": render_path,
            "mux_error": "FFmpeg timed out",
        }
    except FileNotFoundError:
        print("   ❌ FFmpeg not found. Install with: brew install ffmpeg")
        return {
            "final_video_path": render_path,
            "mux_error": "FFmpeg not installed",
        }
    except Exception as e:
        print(f"   ❌ Mux error: {e}")
        return {
            "final_video_path": render_path,
            "mux_error": str(e),
        }


# ─────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────

def generate_music_for_project(
    video_project_id: str,
    refine_with_llm: bool = True,
    output_dir: Optional[Path] = None,
) -> GenerationResult:
    """
    Full music generation pipeline for a video project.
    
    1. Analyzes the video timeline
    2. Optionally refines the composition plan with LLM
    3. Generates the music
    4. Returns the result
    
    This is the main function to call from outside the module.
    """
    from editor.music_planner import analyze_timeline_for_music, print_music_analysis
    
    # Analyze
    print("\n🎵 Analyzing video timeline...")
    analysis = analyze_timeline_for_music(video_project_id)
    print_music_analysis(analysis)
    
    # Refine
    if refine_with_llm:
        print("\n📝 Refining composition plan with LLM...")
        composition_plan = generate_refined_composition_plan(analysis)
    else:
        composition_plan = analysis["composition_plan"]
    
    # Generate
    print("\n🎹 Generating music...")
    generator = MusicGenerator()
    
    if output_dir:
        output_path = output_dir / f"{video_project_id}_bgm.mp3"
    else:
        output_path = Path(f"assets/audio/{video_project_id}_bgm.mp3")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    result = generator.generate_from_composition_plan(
        composition_plan=composition_plan,
        output_path=output_path,
        respect_durations=True,
    )
    
    result.tempo = analysis["recommended_tempo"]
    
    print(f"\n✓ Music generated: {result.output_path}")
    return result


# ─────────────────────────────────────────────────────────────
# Presets for Quick Generation
# ─────────────────────────────────────────────────────────────

PRODUCT_HUNT_TEMPLATES = {
    "standard_demo": """
        Modern tech startup background music, 118-122 BPM,
        clean electronic production with light synth arpeggios and soft drums.
        Optimistic and professional mood.
        Structure: gentle intro for first 8 seconds,
        main upbeat section,
        subtle outro with fade.
        Instrumental only.
    """,

    "exciting_launch": """
        High-energy product launch music, 125 BPM in G major,
        driving electronic beat with punchy drums and bright synth layers.
        Building excitement throughout, triumphant feel.
        Suitable for tech startup announcement video.
        Instrumental only.
    """,

    "saas_explainer": """
        Corporate tech background music for SaaS explainer video,
        moderate tempo 110 BPM, friendly and approachable,
        light piano with modern electronic elements,
        clean and professional mix, not too busy.
        Instrumental only.
    """,

    "feature_walkthrough": """
        Upbeat corporate jingle, 115 BPM,
        bright synthesizers, light percussion, optimistic melody,
        perfect for software feature walkthrough,
        clean radio-ready mix.
        Instrumental only.
    """,
}


def generate_from_template(
    template_name: str,
    duration_seconds: int = 60,
    output_path: Optional[Path] = None,
) -> GenerationResult:
    """
    Quick generation from a preset template.
    
    Available templates:
    - standard_demo
    - exciting_launch
    - saas_explainer
    - feature_walkthrough
    """
    if template_name not in PRODUCT_HUNT_TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    
    prompt = PRODUCT_HUNT_TEMPLATES[template_name].strip()
    
    generator = MusicGenerator()
    return generator.generate_from_prompt(
        prompt=prompt,
        duration_seconds=duration_seconds,
        output_path=output_path,
        force_instrumental=True,
    )
