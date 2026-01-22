"""
Music Planner

Analyzes the video timeline and generates an ElevenLabs composition plan
that aligns musical changes with visual beats.

## Core Insight

The editor's clip tasks already contain the "visual score":
- Timing: start_time_s, duration_s
- Energy: inferred from animation type, text size, composer notes
- Moment type: hero punch, build, reveal, CTA

This planner:
1. Extracts hit points and energy levels from clips
2. Groups clips into musical sections
3. Generates a composition plan with aligned durations
4. The music will have natural transitions at visual beat boundaries

## Energy Inference Rules

| Signal | Energy Level |
|--------|--------------|
| fontSize ≥ 140 | HIGH (hero) |
| animation: scale, pop, glitch | HIGH (punch) |
| animation: typewriter, stagger | MEDIUM (build) |
| animation: fade, reveal | MEDIUM-LOW (smooth) |
| CTA text, "start", "try" | RESOLVE (outro) |
| Short duration (< 0.6s) | HIGH (rapid cuts) |
"""
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass
from enum import Enum
import json
import re


class EnergyLevel(Enum):
    """Musical energy levels mapped to visual intensity."""
    IMPACT = "impact"      # Single word punches, hero moments
    HIGH = "high"          # Fast cuts, energetic reveals
    MEDIUM = "medium"      # Feature walkthroughs, explanations
    LOW = "low"            # Transitions, builds
    RESOLVE = "resolve"    # Outros, CTAs, soft endings


@dataclass
class HitPoint:
    """A significant moment in the video timeline."""
    time_s: float
    duration_s: float
    energy: EnergyLevel
    moment_type: str  # "hero", "feature", "transition", "cta"
    description: str  # Brief description for context
    text_content: Optional[str] = None


@dataclass
class MusicSection:
    """A section in the composition plan."""
    name: str
    duration_ms: int
    energy: EnergyLevel
    positive_styles: List[str]
    negative_styles: List[str]
    aligned_clips: List[str]  # Clip IDs for debugging


# ─────────────────────────────────────────────────────────────
# Energy Inference from Clip Data
# ─────────────────────────────────────────────────────────────

def infer_energy_from_clip(clip_task: dict) -> EnergyLevel:
    """
    Infer energy level from clip task data.
    
    Uses:
    - Animation type (from composer_notes or clip_spec)
    - Text size (from clip_spec layers)
    - Duration (shorter = higher energy)
    - Keywords in composer_notes
    """
    notes = (clip_task.get("composer_notes") or "").lower()
    spec = clip_task.get("clip_spec") or {}
    layers = spec.get("layers") or []
    duration = clip_task.get("duration_s", 1.0)
    
    # Check for explicit energy signals in notes
    if any(word in notes for word in ["punch", "hero", "impact", "explosive", "bang"]):
        return EnergyLevel.IMPACT
    
    if any(word in notes for word in ["cta", "call to action", "start free", "try now", "download"]):
        return EnergyLevel.RESOLVE
    
    # Check animation types
    high_energy_animations = ["scale", "pop", "glitch", "stagger"]
    medium_animations = ["typewriter", "slide_up", "slide_down", "reveal"]
    low_animations = ["fade", "none"]
    
    for layer in layers:
        if layer.get("type") == "text":
            anim = layer.get("animation", {})
            enter = anim.get("enter", "")
            
            # Check text size
            style = layer.get("style", {})
            font_size = style.get("fontSize", 48)
            
            if font_size >= 140:
                return EnergyLevel.IMPACT
            
            if enter in high_energy_animations:
                return EnergyLevel.HIGH
            if enter in medium_animations:
                return EnergyLevel.MEDIUM
    
    # Duration-based inference
    if duration < 0.6:
        return EnergyLevel.HIGH  # Rapid cuts = high energy
    elif duration < 1.0:
        return EnergyLevel.MEDIUM
    else:
        return EnergyLevel.LOW
    
    return EnergyLevel.MEDIUM


def infer_moment_type(clip_task: dict) -> str:
    """Categorize the clip into moment types for musical mapping."""
    notes = (clip_task.get("composer_notes") or "").lower()
    spec = clip_task.get("clip_spec") or {}
    layers = spec.get("layers") or []
    
    # Check for specific patterns
    if any(word in notes for word in ["hero", "title", "brand", "logo"]):
        return "hero"
    
    if any(word in notes for word in ["cta", "call to action", "start", "try", "download", "free"]):
        return "cta"
    
    if any(word in notes for word in ["feature", "screenshot", "demo", "walkthrough"]):
        return "feature"
    
    if any(word in notes for word in ["build", "transition", "bridge"]):
        return "transition"
    
    # Check for image layers (likely feature demo)
    for layer in layers:
        if layer.get("type") == "image":
            return "feature"
    
    # Check text content for hero words
    for layer in layers:
        if layer.get("type") == "text":
            content = layer.get("content", "")
            # Single word, all caps = hero
            if len(content.split()) == 1 and content.isupper():
                return "hero"
    
    return "general"


def extract_text_content(clip_task: dict) -> Optional[str]:
    """Extract primary text content from clip."""
    spec = clip_task.get("clip_spec") or {}
    layers = spec.get("layers") or []
    
    for layer in layers:
        if layer.get("type") == "text":
            return layer.get("content")
    
    return None


# ─────────────────────────────────────────────────────────────
# Hit Point Extraction
# ─────────────────────────────────────────────────────────────

def extract_hit_points(clip_tasks: List[dict]) -> List[HitPoint]:
    """
    Extract hit points from composed clip tasks.
    
    Each clip boundary is a potential hit point.
    We also identify significant internal moments.
    """
    hit_points = []
    
    for task in clip_tasks:
        energy = infer_energy_from_clip(task)
        moment_type = infer_moment_type(task)
        text_content = extract_text_content(task)
        
        # Brief description for context
        description = f"{moment_type}: {text_content or 'visual moment'}"
        
        hit_point = HitPoint(
            time_s=task["start_time_s"],
            duration_s=task["duration_s"],
            energy=energy,
            moment_type=moment_type,
            description=description,
            text_content=text_content,
        )
        
        hit_points.append(hit_point)
    
    # Sort by time
    hit_points.sort(key=lambda h: h.time_s)
    
    return hit_points


# ─────────────────────────────────────────────────────────────
# Musical Section Generation
# ─────────────────────────────────────────────────────────────

# Style mappings based on energy level
ENERGY_STYLES = {
    EnergyLevel.IMPACT: {
        "positive": [
            "punchy kick", "impact hits", "bright stabs", 
            "energetic", "driving", "powerful bass drop"
        ],
        "negative": [
            "soft", "ambient", "filtered", "building", "sparse"
        ],
    },
    EnergyLevel.HIGH: {
        "positive": [
            "full beat", "driving rhythm", "bright arpeggios",
            "synth leads", "energetic", "uptempo"
        ],
        "negative": [
            "minimal", "slow", "ambient", "lo-fi"
        ],
    },
    EnergyLevel.MEDIUM: {
        "positive": [
            "steady groove", "melodic elements", "balanced mix",
            "light percussion", "synth pads"
        ],
        "negative": [
            "heavy bass", "intense", "chaotic"
        ],
    },
    EnergyLevel.LOW: {
        "positive": [
            "filtered", "building tension", "soft synths",
            "subtle rhythm", "atmospheric"
        ],
        "negative": [
            "heavy drums", "intense drops", "loud"
        ],
    },
    EnergyLevel.RESOLVE: {
        "positive": [
            "resolved melody", "gentle fadeout", "satisfying ending",
            "soft landing", "warm tones"
        ],
        "negative": [
            "building", "intense", "aggressive", "rising"
        ],
    },
}


def group_hit_points_into_sections(
    hit_points: List[HitPoint],
    min_section_duration_ms: int = 2000,  # Minimum 2 seconds per section
) -> List[MusicSection]:
    """
    Group consecutive hit points with similar energy into musical sections.
    
    This prevents too many tiny sections that would sound choppy.
    Adjacent clips with same energy level are merged.
    """
    if not hit_points:
        return []
    
    sections = []
    current_group = [hit_points[0]]
    current_energy = hit_points[0].energy
    
    for hp in hit_points[1:]:
        # Check if we should continue the current group
        # Same energy level = merge
        # Different energy but accumulated duration too short = merge anyway
        current_duration_ms = sum(h.duration_s * 1000 for h in current_group)
        
        if hp.energy == current_energy or current_duration_ms < min_section_duration_ms:
            current_group.append(hp)
            # Update energy to the highest in the group
            if hp.energy.value < current_energy.value:  # Lower enum value = higher energy
                current_energy = hp.energy
        else:
            # Create section from current group
            section = create_section_from_group(current_group, len(sections) + 1)
            sections.append(section)
            
            # Start new group
            current_group = [hp]
            current_energy = hp.energy
    
    # Don't forget the last group
    if current_group:
        section = create_section_from_group(current_group, len(sections) + 1)
        sections.append(section)
    
    return sections


def create_section_from_group(hit_points: List[HitPoint], section_num: int) -> MusicSection:
    """Create a MusicSection from a group of hit points."""
    # Calculate duration
    total_duration_ms = int(sum(hp.duration_s * 1000 for hp in hit_points))
    
    # Determine dominant energy (most impactful wins)
    energy_priority = [
        EnergyLevel.IMPACT,
        EnergyLevel.HIGH,
        EnergyLevel.MEDIUM,
        EnergyLevel.RESOLVE,
        EnergyLevel.LOW,
    ]
    
    energies = [hp.energy for hp in hit_points]
    dominant_energy = min(energies, key=lambda e: energy_priority.index(e))
    
    # Determine moment type for naming
    moment_types = [hp.moment_type for hp in hit_points]
    if "hero" in moment_types:
        section_type = "Hero"
    elif "cta" in moment_types:
        section_type = "CTA"
    elif "feature" in moment_types:
        section_type = "Feature"
    else:
        section_type = "Flow"
    
    # Get styles for this energy level
    styles = ENERGY_STYLES[dominant_energy]
    
    # Create section name
    name = f"{section_type} {section_num} ({dominant_energy.value})"
    
    return MusicSection(
        name=name,
        duration_ms=total_duration_ms,
        energy=dominant_energy,
        positive_styles=styles["positive"],
        negative_styles=styles["negative"],
        aligned_clips=[hp.description for hp in hit_points],
    )


# ─────────────────────────────────────────────────────────────
# Composition Plan Generation
# ─────────────────────────────────────────────────────────────

def build_composition_plan(
    sections: List[MusicSection],
    global_style: str = "modern electronic tech startup",
    tempo_hint: int = 120,
) -> dict:
    """
    Build an ElevenLabs composition_plan from music sections.
    
    The composition plan uses:
    - positiveGlobalStyles: Overall vibe
    - negativeGlobalStyles: What to avoid
    - sections[]: Each section with local styles and exact duration
    """
    # Global styles based on Product Hunt aesthetic
    positive_global = [
        "modern electronic",
        "tech startup",
        "clean production",
        "upbeat",
        f"{tempo_hint} BPM",
        "professional",
    ]
    
    negative_global = [
        "acoustic",
        "slow",
        "lo-fi",
        "ambient",
        "vocals",
        "dark",
        "melancholic",
    ]
    
    # Build sections array
    plan_sections = []
    for section in sections:
        plan_section = {
            "sectionName": section.name,
            "durationMs": section.duration_ms,
            "positiveLocalStyles": section.positive_styles[:5],  # ElevenLabs limit
            "negativeLocalStyles": section.negative_styles[:5],
            "lines": [],  # No lyrics for instrumental
        }
        plan_sections.append(plan_section)

    # NOTE: 程序化合并逻辑已注释，由 LLM 负责合并短 sections
    # LLM 会根据 ElevenLabs API 约束（>= 3000ms）自动合并
    # 这样逻辑更统一，LLM 有完全的控制权

    # # 合并短 sections（ElevenLabs 要求每个 section >= 3000ms）
    # MIN_SECTION_DURATION = 3000
    # merged = []
    # accumulator = None
    #
    # for section in plan_sections:
    #     if accumulator is None:
    #         accumulator = section
    #     else:
    #         # 累积合并
    #         accumulator = {
    #             "sectionName": f"{accumulator['sectionName']} + {section['sectionName']}",
    #             "durationMs": accumulator["durationMs"] + section["durationMs"],
    #             "positiveLocalStyles": accumulator["positiveLocalStyles"] + section["positiveLocalStyles"],
    #             "negativeLocalStyles": accumulator["negativeLocalStyles"] + section["negativeLocalStyles"],
    #             "lines": []
    #         }
    #
    #     # 只有当累积的 duration >= 3000ms 时才添加到 merged
    #     if accumulator["durationMs"] >= MIN_SECTION_DURATION:
    #         merged.append(accumulator)
    #         accumulator = None
    #
    # # 处理最后的累积器
    # if accumulator:
    #     if merged:
    #         # 合并到最后一个 section
    #         last = merged[-1]
    #         merged[-1] = {
    #             "sectionName": f"{last['sectionName']} + {accumulator['sectionName']}",
    #             "durationMs": last["durationMs"] + accumulator["durationMs"],
    #             "positiveLocalStyles": last["positiveLocalStyles"] + accumulator["positiveLocalStyles"],
    #             "negativeLocalStyles": last["negativeLocalStyles"] + accumulator["negativeLocalStyles"],
    #             "lines": []
    #         }
    #     else:
    #         # 如果所有 sections 加起来都 < 3000ms，只能添加这个不符合要求的 section
    #         merged.append(accumulator)
    #
    # plan_sections = merged

    composition_plan = {
        "positiveGlobalStyles": positive_global,
        "negativeGlobalStyles": negative_global,
        "sections": plan_sections,
    }
    
    return composition_plan


# ─────────────────────────────────────────────────────────────
# Main Interface
# ─────────────────────────────────────────────────────────────

def analyze_timeline_for_music(video_project_id: str) -> dict:
    """
    Analyze video timeline and return music generation context.
    
    Returns:
        {
            "hit_points": [...],
            "sections": [...],
            "composition_plan": {...},
            "total_duration_ms": int,
            "recommended_tempo": int,
            "energy_curve": str,
        }
    """
    from db.supabase_client import get_client
    
    client = get_client()
    
    # Load composed clip tasks
    result = client.table("clip_tasks").select("*").eq(
        "video_project_id", video_project_id
    ).eq("status", "composed").order("start_time_s").execute()
    
    clip_tasks = result.data or []
    
    if not clip_tasks:
        raise ValueError("No composed clips found. Run editor first.")
    
    # Extract hit points
    hit_points = extract_hit_points(clip_tasks)
    
    # Calculate total duration
    if hit_points:
        last_hp = max(hit_points, key=lambda h: h.time_s + h.duration_s)
        total_duration_ms = int((last_hp.time_s + last_hp.duration_s) * 1000)
    else:
        total_duration_ms = 30000  # Default 30s
    
    # Group into sections
    sections = group_hit_points_into_sections(hit_points)
    
    # Determine recommended tempo based on clip density
    clips_per_second = len(clip_tasks) / (total_duration_ms / 1000)
    if clips_per_second > 1.5:
        recommended_tempo = 125  # Fast cuts need faster tempo
    elif clips_per_second > 1.0:
        recommended_tempo = 120
    else:
        recommended_tempo = 115
    
    # Build composition plan
    composition_plan = build_composition_plan(sections, tempo_hint=recommended_tempo)
    
    # Describe energy curve
    if sections:
        curve_parts = []
        for s in sections:
            curve_parts.append(s.energy.value)
        energy_curve = " → ".join(curve_parts)
    else:
        energy_curve = "steady"
    
    return {
        "hit_points": [
            {
                "time_s": hp.time_s,
                "duration_s": hp.duration_s,
                "energy": hp.energy.value,
                "moment_type": hp.moment_type,
                "description": hp.description,
            }
            for hp in hit_points
        ],
        "sections": [
            {
                "name": s.name,
                "duration_ms": s.duration_ms,
                "energy": s.energy.value,
                "aligned_clips": s.aligned_clips,
            }
            for s in sections
        ],
        "composition_plan": composition_plan,
        "total_duration_ms": total_duration_ms,
        "recommended_tempo": recommended_tempo,
        "energy_curve": energy_curve,
        "clip_density": clips_per_second,
    }


def print_music_analysis(analysis: dict):
    """Print a human-readable summary of the music analysis."""
    print("\n🎵 Music Analysis")
    print(f"   Total duration: {analysis['total_duration_ms'] / 1000:.1f}s")
    print(f"   Clip density: {analysis['clip_density']:.2f} clips/second")
    print(f"   Recommended tempo: {analysis['recommended_tempo']} BPM")
    print(f"   Energy curve: {analysis['energy_curve']}")
    
    print(f"\n   Hit Points ({len(analysis['hit_points'])}):")
    for hp in analysis['hit_points'][:10]:  # Show first 10
        print(f"      {hp['time_s']:.1f}s | {hp['energy']:8s} | {hp['description']}")
    
    if len(analysis['hit_points']) > 10:
        print(f"      ... and {len(analysis['hit_points']) - 10} more")
    
    print(f"\n   Music Sections ({len(analysis['sections'])}):")
    for s in analysis['sections']:
        print(f"      {s['name']} ({s['duration_ms']/1000:.1f}s)")


# ─────────────────────────────────────────────────────────────
# LangGraph Node
# ─────────────────────────────────────────────────────────────

def music_planner_node(state: dict) -> dict:
    """
    LangGraph node: Analyze timeline and prepare music generation.
    """
    print("\n🎵 Analyzing timeline for music generation...")
    
    video_project_id = state["video_project_id"]
    
    try:
        analysis = analyze_timeline_for_music(video_project_id)
        print_music_analysis(analysis)
        
        return {
            "music_analysis": analysis,
            "composition_plan": analysis["composition_plan"],
        }
        
    except Exception as e:
        print(f"\n❌ Music analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "music_analysis": None,
            "composition_plan": None,
            "render_error": str(e),
        }
