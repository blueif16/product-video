# Music Generation Strategy

How to generate background music that perfectly fits your video's tempo and hit points.

---

## Core Concept: Visual Score → Musical Score

Your editor's clip tasks already contain a **visual score**:
- **Timing**: `start_time_s`, `duration_s`
- **Energy**: Inferred from animation type, text size, composer notes
- **Moment Type**: Hero punch, feature reveal, transition, CTA

The music planner translates this into a **musical score** via ElevenLabs' composition plan.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MUSIC GENERATION PIPELINE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. ANALYZE CLIP TIMELINE (music_planner.py)                               │
│     └─→ Extract from composed clips:                                        │
│         - Hit points (clip start times = visual beats)                     │
│         - Energy levels (infer from animation/text size)                   │
│         - Moment types (hero/build/reveal/cta)                             │
│                                                                             │
│  2. GROUP INTO SECTIONS                                                     │
│     └─→ Adjacent clips with similar energy → merge into sections           │
│     └─→ Ensures minimum 2s per section (avoid choppy music)                │
│                                                                             │
│  3. BUILD COMPOSITION PLAN                                                  │
│     └─→ Generate ElevenLabs composition_plan:                              │
│         - positiveGlobalStyles: overall vibe                               │
│         - negativeGlobalStyles: what to avoid                              │
│         - sections[]: exact durations aligned to visual beats              │
│                                                                             │
│  4. (OPTIONAL) LLM REFINEMENT                                              │
│     └─→ LLM improves style descriptors for better results                  │
│     └─→ Keeps durations EXACTLY the same (alignment is sacred)             │
│                                                                             │
│  5. GENERATE WITH ELEVENLABS                                               │
│     └─→ respect_sections_durations=True ensures alignment                  │
│     └─→ Musical transitions occur at visual beat boundaries                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Energy Inference Rules

The music planner infers energy levels from clip data:

| Visual Signal | Energy Level | Musical Treatment |
|---------------|--------------|-------------------|
| `fontSize ≥ 140` | **IMPACT** | Punchy kick, impact hits, bright stabs |
| Animation: scale, pop, glitch | **HIGH** | Full beat, driving rhythm |
| Animation: typewriter, stagger | **MEDIUM** | Steady groove, arpeggios |
| Animation: fade, reveal | **LOW** | Filtered, building tension |
| CTA text ("start free") | **RESOLVE** | Gentle fadeout, resolved melody |
| Duration < 0.6s | **HIGH** | Fast music matches rapid cuts |

---

## Section Grouping Strategy

Adjacent clips with similar energy are merged into sections:

```
Clips:                  Sections:
─────                   ─────────
0.0s: IMPACT           ┐
0.5s: IMPACT           ├─ "Hero 1 (impact)" - 1.5s
1.0s: HIGH             ┘

1.5s: MEDIUM           ┐
2.1s: MEDIUM           ├─ "Feature 2 (medium)" - 3.0s
3.5s: MEDIUM           ┘

4.5s: RESOLVE          ─  "CTA 3 (resolve)" - 2.0s
```

**Why merge?** 
- Too many tiny sections = choppy music
- ElevenLabs needs time to develop each section
- Minimum 2 seconds per section for musical coherence

---

## Composition Plan Structure

```json
{
  "positiveGlobalStyles": [
    "modern electronic",
    "tech startup",
    "clean production",
    "upbeat",
    "120 BPM",
    "professional"
  ],
  "negativeGlobalStyles": [
    "acoustic", "slow", "lo-fi", "ambient", "vocals", "dark"
  ],
  "sections": [
    {
      "sectionName": "Hero 1 (impact)",
      "durationMs": 1500,
      "positiveLocalStyles": ["punchy kick", "impact hits", "bright stabs", "energetic"],
      "negativeLocalStyles": ["soft", "ambient", "filtered", "building"],
      "lines": []
    },
    {
      "sectionName": "Feature 2 (medium)",
      "durationMs": 3000,
      "positiveLocalStyles": ["steady groove", "melodic elements", "synth pads"],
      "negativeLocalStyles": ["heavy bass", "intense", "chaotic"],
      "lines": []
    },
    {
      "sectionName": "CTA 3 (resolve)",
      "durationMs": 2000,
      "positiveLocalStyles": ["resolved melody", "gentle fadeout", "warm tones"],
      "negativeLocalStyles": ["building", "intense", "aggressive"],
      "lines": []
    }
  ]
}
```

---

## Tempo Selection

Based on clip density (clips per second):

| Clip Density | Recommended Tempo | Video Type |
|--------------|-------------------|------------|
| > 1.5 clips/sec | 125 BPM | Fast-paced, TikTok energy |
| 1.0-1.5 clips/sec | 120 BPM | Standard Product Hunt |
| < 1.0 clips/sec | 115 BPM | Explainer, walkthrough |

---

## Style Vocabulary

### Energy: IMPACT (Hero Moments)
**Positive**: punchy kick, impact hits, bright stabs, energetic, driving, powerful bass drop
**Negative**: soft, ambient, filtered, building, sparse

### Energy: HIGH (Fast Cuts)
**Positive**: full beat, driving rhythm, bright arpeggios, synth leads, uptempo
**Negative**: minimal, slow, ambient, lo-fi

### Energy: MEDIUM (Features)
**Positive**: steady groove, melodic elements, balanced mix, light percussion, synth pads
**Negative**: heavy bass, intense, chaotic

### Energy: LOW (Transitions)
**Positive**: filtered, building tension, soft synths, subtle rhythm, atmospheric
**Negative**: heavy drums, intense drops, loud

### Energy: RESOLVE (CTA/Outro)
**Positive**: resolved melody, gentle fadeout, satisfying ending, soft landing, warm tones
**Negative**: building, intense, aggressive, rising

---

## LLM Refinement Prompt

When using LLM to refine the composition plan:

```
You are a music director for Product Hunt videos. Refine this composition plan.

## VIDEO CONTEXT
Total Duration: {total}s
Clip Density: {density} clips/second
Energy Curve: {curve}
Recommended Tempo: {tempo} BPM

## HIT POINTS
{list of hit points with timing and energy}

## PROPOSED SECTIONS
{list of sections}

## YOUR TASK
Refine the positiveLocalStyles and negativeLocalStyles for each section.

Rules:
- Keep section durations EXACTLY as specified (alignment is critical)
- Each section should have 3-5 styles (not more)
- Be specific: "punchy side-chain kick" > "drums"
- Match the energy curve of the video

Return ONLY the refined JSON composition plan.
```

---

## Integration Example

```python
from src.tools.music_generator import generate_music_for_project

# Full pipeline: analyze → refine → generate
result = generate_music_for_project(
    video_project_id="abc123",
    refine_with_llm=True,
)

print(f"Generated: {result.output_path}")
print(f"Duration: {result.duration_ms}ms")
print(f"Tempo: {result.tempo} BPM")
```

Or step by step:

```python
from src.editor.music_planner import analyze_timeline_for_music
from src.tools.music_generator import MusicGenerator, generate_refined_composition_plan

# 1. Analyze
analysis = analyze_timeline_for_music("abc123")

# 2. Refine (optional)
refined_plan = generate_refined_composition_plan(analysis)

# 3. Generate
generator = MusicGenerator()
result = generator.generate_from_composition_plan(
    composition_plan=refined_plan,
    output_path=Path("output.mp3"),
)
```

---

## Debugging Tips

### Check Hit Point Extraction
```python
from src.editor.music_planner import analyze_timeline_for_music, print_music_analysis

analysis = analyze_timeline_for_music("your-project-id")
print_music_analysis(analysis)
```

### Inspect Composition Plan
```python
import json
print(json.dumps(analysis["composition_plan"], indent=2))
```

### Verify Section Alignment
The sum of all `durationMs` should equal your video duration:
```python
total_ms = sum(s["durationMs"] for s in plan["sections"])
print(f"Total: {total_ms}ms")
```

---

## Common Issues

### Music doesn't align with visual beats
- Check that `respect_sections_durations=True` in generate call
- Verify section durations match clip boundaries exactly

### Music sounds choppy
- Sections might be too short
- Increase `min_section_duration_ms` in music_planner

### Wrong energy vibe
- Check energy inference rules
- Override with explicit composer_notes keywords like "punchy", "calm"

### Generation fails
- Check ELEVENLABS_API_KEY is set
- Verify section durations are within 3-600 seconds range
