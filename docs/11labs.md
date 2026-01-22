# ElevenLabs Eleven Music Developer Guide
## For Product Hunt Video BGM & Instrumental Tracks

> Generate studio-grade background music with precise tempo/flow control via prompts

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [API Reference](#api-reference)
3. [Prompting Best Practices](#prompting-best-practices)
4. [Composition Plans (Advanced Control)](#composition-plans)
5. [Product Hunt BGM Prompt Templates](#product-hunt-bgm-templates)
6. [Code Examples](#code-examples)

---

## Quick Start

### Installation

```bash
# Python
pip install elevenlabs python-dotenv

# Node.js
npm install elevenlabs dotenv
```

### Environment Setup

```bash
# .env
ELEVENLABS_API_KEY=your_api_key_here
```

### Minimal Example

```python
from elevenlabs.client import ElevenLabs
import os
from dotenv import load_dotenv

load_dotenv()

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Generate 60-second Product Hunt style BGM
track = client.music.compose(
    prompt="Upbeat corporate tech background music, 120 BPM, modern electronic with light synths, optimistic and clean, instrumental only",
    music_length_ms=60000,
    force_instrumental=True,
)

with open("product_hunt_bgm.mp3", "wb") as f:
    for chunk in track:
        f.write(chunk)
```

---

## API Reference

### Endpoint
```
POST https://api.elevenlabs.io/v1/music
```

### Headers
```
xi-api-key: your_api_key
Content-Type: application/json
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes* | Natural language description (max 4100 chars). Cannot use with `composition_plan` |
| `composition_plan` | object | Yes* | Detailed section-by-section plan. Cannot use with `prompt` |
| `music_length_ms` | integer | No | Duration: 3000-600000ms (3s to 5min). Auto-determined if omitted |
| `model_id` | string | No | Default: `music_v1` |
| `force_instrumental` | boolean | No | `true` = guaranteed no vocals (default: false) |
| `output_format` | string | No | Default: `mp3_44100_128`. Options: mp3/pcm variants |
| `respect_sections_durations` | boolean | No | Strict timing adherence for composition_plan |

### cURL Example
```bash
curl -X POST https://api.elevenlabs.io/v1/music \
  -H "xi-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Modern tech startup background music, 115 BPM, upbeat electronic, clean mix, instrumental only",
    "music_length_ms": 90000,
    "force_instrumental": true
  }' --output bgm.mp3
```

---

## Prompting Best Practices

### Core Principles

1. **Describe, don't command** - Say "upbeat electronic track" not "create an upbeat track"
2. **Include use case** - "background music for tech product demo" helps AI infer appropriate structure
3. **Be specific but not verbose** - Concise prompts often outperform long ones

### Prompt Formula for BGM

```
[GENRE/STYLE] + [TEMPO/BPM] + [KEY (optional)] + [INSTRUMENTS] + [MOOD/ENERGY] + [USE CASE] + "instrumental only"
```

### Musical Control Elements

| Element | How to Specify | Examples |
|---------|---------------|----------|
| **Tempo** | Include BPM directly | `120 BPM`, `fast-paced 140 BPM` |
| **Key** | Specify key signature | `in C major`, `in A minor` |
| **Energy** | Mood descriptors | `uplifting`, `energetic`, `calm`, `building` |
| **Instruments** | Name them with "solo" prefix for isolation | `synth arpeggios`, `solo piano`, `punchy drums` |
| **No vocals** | Explicit instruction | `instrumental only`, `no vocals` |
| **Structure timing** | Time-based cues | `soft intro for 10 seconds, then energetic` |

### Effective Mood Descriptors

```
Abstract: eerie, foreboding, triumphant, melancholic, euphoric, hopeful
Technical: dissonant, minor key, major key, syncopated, driving, ambient
Production: clean mix, punchy, warm, bright, lo-fi, polished
```

### What Works Best

✅ **Good Prompts:**
```
"Upbeat corporate jingle with bright synthesizers, punchy drums, and an optimistic melody, 118 BPM, instrumental only"

"Modern tech product demo music, clean electronic, building energy, 120 BPM in G major, suitable for startup video"

"Background music for a coffee shop commercial, friendly and inviting, acoustic guitar with light electronic touches"
```

❌ **Avoid:**
```
"Create a song that sounds like [artist name]"  # Copyright blocked
"Make me some music"  # Too vague
"Happy upbeat fun exciting energetic powerful music with guitars and synths and drums"  # Conflicting/overloaded
```

---

## Composition Plans

For **precise control over sections and flow**, use composition plans instead of simple prompts.

### Structure

```json
{
  "positiveGlobalStyles": ["electronic", "upbeat", "modern"],
  "negativeGlobalStyles": ["acoustic", "slow", "lo-fi"],
  "sections": [
    {
      "sectionName": "Intro",
      "positiveLocalStyles": ["soft synth pad", "filtered", "building tension"],
      "negativeLocalStyles": ["heavy drums", "vocals"],
      "durationMs": 10000,
      "lines": []
    },
    {
      "sectionName": "Main Theme",
      "positiveLocalStyles": ["full drums", "bright arpeggios", "energetic"],
      "negativeLocalStyles": ["ambient", "sparse"],
      "durationMs": 40000,
      "lines": []
    },
    {
      "sectionName": "Outro",
      "positiveLocalStyles": ["fade out", "softer", "resolved"],
      "negativeLocalStyles": ["building", "intense"],
      "durationMs": 10000,
      "lines": []
    }
  ]
}
```

### Generate Composition Plan from Prompt

```python
# Auto-generate a plan from natural language
composition_plan = client.music.composition_plan.create(
    prompt="Product Hunt demo video BGM: soft intro, energetic middle section, calm outro. 120 BPM, modern electronic, 60 seconds total",
    music_length_ms=60000,
)

print(composition_plan)  # Review/edit the plan

# Then generate music from the plan
track = client.music.compose(
    composition_plan=composition_plan
)
```

---

## Product Hunt BGM Templates

### Template 1: Standard Product Demo (60s)

```python
PROMPT = """
Modern tech startup background music, 118-122 BPM, 
clean electronic production with light synth arpeggios and soft drums.
Optimistic and professional mood.
Structure: gentle intro for first 8 seconds, 
main upbeat section, 
subtle outro with fade.
Instrumental only.
"""
```

### Template 2: Exciting Launch Video (90s)

```python
PROMPT = """
High-energy product launch music, 125 BPM in G major,
driving electronic beat with punchy drums and bright synth layers.
Building excitement throughout, triumphant feel.
Suitable for tech startup announcement video.
Instrumental only.
"""
```

### Template 3: SaaS Explainer (2 min)

```python
PROMPT = """
Corporate tech background music for SaaS explainer video,
moderate tempo 110 BPM, friendly and approachable,
light piano with modern electronic elements,
clean and professional mix, not too busy.
Instrumental only.
"""
```

### Template 4: Feature Walkthrough (45s)

```python
PROMPT = """
Upbeat corporate jingle, 115 BPM,
bright synthesizers, light percussion, optimistic melody,
perfect for software feature walkthrough,
clean radio-ready mix.
Instrumental only.
"""
```

### Template 5: Composition Plan for Dynamic Flow

```python
COMPOSITION_PLAN = {
    "positiveGlobalStyles": [
        "electronic", "corporate", "modern", "clean mix", "upbeat"
    ],
    "negativeGlobalStyles": [
        "acoustic", "slow", "dark", "ambient", "lo-fi", "vocals"
    ],
    "sections": [
        {
            "sectionName": "Intro",
            "positiveLocalStyles": [
                "soft filtered synth", "building anticipation", "light hi-hats"
            ],
            "negativeLocalStyles": ["heavy bass", "loud drums"],
            "durationMs": 8000,
            "lines": []
        },
        {
            "sectionName": "Main Section",
            "positiveLocalStyles": [
                "full beat", "bright arpeggios", "energetic", "driving rhythm"
            ],
            "negativeLocalStyles": ["sparse", "minimal"],
            "durationMs": 35000,
            "lines": []
        },
        {
            "sectionName": "Bridge/Build",
            "positiveLocalStyles": [
                "rising tension", "filter sweep", "snare roll"
            ],
            "negativeLocalStyles": ["resolution", "calm"],
            "durationMs": 7000,
            "lines": []
        },
        {
            "sectionName": "Outro",
            "positiveLocalStyles": [
                "gentle fadeout", "resolved", "soft ending"
            ],
            "negativeLocalStyles": ["abrupt", "building"],
            "durationMs": 10000,
            "lines": []
        }
    ]
}
```

---

## Code Examples

### Python: Full Implementation

```python
from elevenlabs.client import ElevenLabs
import os
from dotenv import load_dotenv

load_dotenv()

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def generate_product_hunt_bgm(
    duration_seconds: int = 60,
    tempo: int = 120,
    energy: str = "upbeat",
    output_path: str = "bgm.mp3"
):
    """Generate Product Hunt style BGM with customizable parameters."""
    
    prompt = f"""
    Modern tech startup background music, {tempo} BPM,
    clean electronic production with synth arpeggios and light drums.
    {energy.capitalize()} and professional mood.
    Suitable for product demo or launch video.
    Instrumental only.
    """
    
    track = client.music.compose(
        prompt=prompt,
        music_length_ms=duration_seconds * 1000,
        force_instrumental=True,
    )
    
    with open(output_path, "wb") as f:
        for chunk in track:
            f.write(chunk)
    
    print(f"✅ Generated: {output_path} ({duration_seconds}s at {tempo} BPM)")
    return output_path


def generate_with_composition_plan(
    plan: dict,
    output_path: str = "bgm_structured.mp3"
):
    """Generate BGM with precise section control."""
    
    track = client.music.compose(
        composition_plan=plan,
        respect_sections_durations=True,
    )
    
    with open(output_path, "wb") as f:
        for chunk in track:
            f.write(chunk)
    
    return output_path


# Usage
if __name__ == "__main__":
    # Simple generation
    generate_product_hunt_bgm(
        duration_seconds=60,
        tempo=118,
        energy="optimistic",
        output_path="demo_bgm.mp3"
    )
    
    # With composition plan for precise flow control
    plan = {
        "positiveGlobalStyles": ["electronic", "modern", "clean"],
        "negativeGlobalStyles": ["acoustic", "slow", "vocals"],
        "sections": [
            {
                "sectionName": "Soft Intro",
                "positiveLocalStyles": ["filtered synth", "building"],
                "negativeLocalStyles": ["heavy drums"],
                "durationMs": 10000,
                "lines": []
            },
            {
                "sectionName": "Main Energy",
                "positiveLocalStyles": ["full beat", "bright", "driving"],
                "negativeLocalStyles": ["minimal"],
                "durationMs": 40000,
                "lines": []
            },
            {
                "sectionName": "Fade Out",
                "positiveLocalStyles": ["gentle", "resolved"],
                "negativeLocalStyles": ["building"],
                "durationMs": 10000,
                "lines": []
            }
        ]
    }
    
    generate_with_composition_plan(plan, "structured_bgm.mp3")
```

### TypeScript/Node.js Implementation

```typescript
import { ElevenLabsClient } from "elevenlabs";
import * as fs from "fs";
import * as dotenv from "dotenv";

dotenv.config();

const client = new ElevenLabsClient({
  apiKey: process.env.ELEVENLABS_API_KEY,
});

async function generateBGM(
  durationSeconds: number = 60,
  tempo: number = 120,
  outputPath: string = "bgm.mp3"
): Promise<void> {
  const prompt = `
    Modern tech startup background music, ${tempo} BPM,
    clean electronic production with synth arpeggios and light drums.
    Optimistic and professional mood.
    Suitable for product demo video.
    Instrumental only.
  `;

  const audio = await client.music.compose({
    prompt: prompt,
    music_length_ms: durationSeconds * 1000,
    force_instrumental: true,
  });

  const chunks: Buffer[] = [];
  for await (const chunk of audio) {
    chunks.push(chunk);
  }

  fs.writeFileSync(outputPath, Buffer.concat(chunks));
  console.log(`✅ Generated: ${outputPath}`);
}

// Run
generateBGM(60, 118, "product_hunt_bgm.mp3");
```

### REST API (cURL)

```bash
# Simple prompt
curl -X POST https://api.elevenlabs.io/v1/music \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Modern tech startup BGM, 120 BPM, clean electronic, upbeat, instrumental only",
    "music_length_ms": 60000,
    "force_instrumental": true
  }' --output bgm.mp3

# With composition plan
curl -X POST https://api.elevenlabs.io/v1/music \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "composition_plan": {
      "positiveGlobalStyles": ["electronic", "upbeat", "modern"],
      "negativeGlobalStyles": ["acoustic", "slow", "vocals"],
      "sections": [
        {
          "sectionName": "Intro",
          "positiveLocalStyles": ["soft", "filtered", "building"],
          "negativeLocalStyles": ["heavy"],
          "durationMs": 10000,
          "lines": []
        },
        {
          "sectionName": "Main",
          "positiveLocalStyles": ["energetic", "full beat", "bright"],
          "negativeLocalStyles": ["minimal"],
          "durationMs": 40000,
          "lines": []
        },
        {
          "sectionName": "Outro",
          "positiveLocalStyles": ["fadeout", "gentle"],
          "negativeLocalStyles": ["building"],
          "durationMs": 10000,
          "lines": []
        }
      ]
    }
  }' --output structured_bgm.mp3
```

---

## Quick Reference Card

### Essential Prompt Elements for Product Hunt BGM

| What You Want | Include in Prompt |
|---------------|-------------------|
| No vocals | `instrumental only` |
| Specific tempo | `120 BPM` |
| Specific key | `in G major` |
| Soft start | `gentle intro for 8 seconds` |
| Building energy | `building tension`, `rising` |
| Fade out | `gentle fadeout ending` |
| Clean sound | `clean mix`, `polished`, `radio-ready` |
| Modern feel | `modern electronic`, `contemporary` |
| Corporate vibe | `corporate`, `professional`, `startup` |

### Tempo Guidelines

| Video Type | Recommended BPM |
|------------|-----------------|
| Calm explainer | 90-110 BPM |
| Standard demo | 110-120 BPM |
| Energetic launch | 120-130 BPM |
| High-intensity promo | 130-150 BPM |

### Output Specs
- **Format:** MP3 (44.1kHz, 128-192kbps)
- **Duration:** 10 seconds to 5 minutes
- **Commercial use:** ✅ Cleared for YouTube, podcasts, ads, games, social media

---

## Pricing Note

ElevenLabs Music pricing is based on **minutes of generated audio**:
- Free tier: 11 minutes/month
- Starter ($5/mo): 22 minutes
- Creator ($22/mo): 62 minutes
- Pro ($99/mo): 304 minutes + commercial licensing

---

## Resources

- [Official Docs](https://elevenlabs.io/docs/overview/capabilities/music)
- [Best Practices](https://elevenlabs.io/docs/overview/capabilities/music/best-practices)
- [API Reference](https://elevenlabs.io/docs/api-reference/music/compose)
- [Music Terms & Licensing](https://elevenlabs.io/terms)