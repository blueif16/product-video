# RAG Knowledge Research Guide

**How to fill up `rag_research_template.json` with high-quality patterns**

---

## Quick Start

1. **Copy the template:**
   ```bash
   cp rag_research_template.json my_research.json
   ```

2. **Fill it with patterns** (see examples below)

3. **Ingest to database:**
   ```bash
   # Dry run first
   python ingest_knowledge.py my_research.json --dry-run
   
   # Actually ingest
   python ingest_knowledge.py my_research.json
   
   # Test your patterns
   python ingest_knowledge.py my_research.json --test "kinetic energy image"
   ```

---

## JSON Structure

```json
{
  "namespace": "remotion_execution_patterns",
  "patterns": [
    {
      "id": "unique_snake_case_id",
      "content": "Self-contained 150-300 word pattern...",
      "metadata": {
        "type": "technique | antipattern | layout | timing | energy_technique | calculation | animation_combo",
        "source": "where_this_came_from"
      },
      "relations": [
        {
          "to_id": "other_pattern_id",
          "relation_type": "requires | works_with | contradicts | implements | applies_to | avoids"
        }
      ]
    }
  ]
}
```

---

## Pattern Types & What They Cover

### 1. `technique` - Core execution methods
**When to use:** Specific animation/composition techniques

**Example:**
```json
{
  "id": "slide_up_text_animation",
  "content": "Slide-Up Text Animation for Impact: Text slides from y:+100 to final position over 15-20 frames using slide_up animation. Works best with feel:\"snappy\" for kinetic energy or feel:\"smooth\" for elegant. Start text completely off-canvas below (y:100+offset) and interpolate to target position. Use with fontSize 80-150 for headlines. Combine with opacity fade (0→1 over same duration) for smoother appearance. This creates upward momentum, suggesting progress or achievement. Apply to: CTAs, feature callouts, headline reveals. Timing: enterDuration 15 frames for kinetic, 20 frames for elegant. Common mistake: Sliding too far (starting y:150) makes animation feel slow, stick to y:105-110 start. Works with: staggered reveals (multiple texts slide up in sequence). Avoid: Sliding down for positive messages (feels like defeat).",
  "metadata": {
    "type": "technique",
    "source": "animation_patterns_research"
  }
}
```

### 2. `antipattern` - Common mistakes to avoid
**When to use:** Documenting errors and how to fix them

**Template:**
```
[Error Name]: [What the mistake is]. [Why it happens]. [Specific examples with numbers]. 
[How to detect it]. [How to fix it]. [How common it is].
```

### 3. `layout` - Spatial composition patterns
**When to use:** How to arrange elements on canvas

**Must include:** Specific x/y positions, scale values, spacing calculations

### 4. `timing` - Frame-based choreography
**When to use:** When/how elements appear over time

**Must include:** Specific frame numbers, duration percentages, reveal sequences

### 5. `energy_technique` - Energy-specific approaches
**When to use:** How to execute a specific energy (kinetic, elegant, etc.)

**Must include:** Animation types, timing values, what makes it feel that way

### 6. `calculation` - Math formulas for positioning
**When to use:** Formulas composers need to calculate positions

**Must include:** The formula, example calculations, edge cases

### 7. `animation_combo` - Proven combinations
**When to use:** Multiple techniques that work well together

**Must include:** What to combine, specific parameters, why it works

---

## Writing High-Quality Content

### The Formula (Every Pattern Needs These)

**1. Name + Core Technique (First Sentence)**
```
"Kinetic Energy Staggered Text Reveals: Use rapid-fire text animations..."
```

**2. Technical Specifics (Numbers!)**
```
"...with 5-10 frame gaps between elements. For a 5-second clip (150 frames), 
start first text at frame 20, second at frame 28, third at frame 36..."
```

**3. Context (When/Where)**
```
"...This creates the punchy, confident energy expected in Product Hunt and 
SaaS demo videos. Works for: tech products, app launches, developer tools."
```

**4. Common Mistakes**
```
"Common mistake: Front-loading all reveals in first 40 frames, leaving 110 
frames static. Instead, spread primary reveals across first 60-70 frames..."
```

**5. Concrete Example**
```
"...Primary text should be 80-120 fontSize, supporting text 32-48 fontSize..."
```

**6. Why It Works (Optional)**
```
"...This maintains continuous engagement throughout the clip rather than 
front-loading then going static."
```

### Content Checklist (Before Adding Pattern)

- [ ] First sentence clearly names the pattern?
- [ ] Includes specific numbers (frame counts, percentages, pixel values)?
- [ ] States when to use / when to avoid?
- [ ] Includes at least one common mistake?
- [ ] Has concrete example with parameters?
- [ ] Is 150-300 words (rich enough but not bloated)?
- [ ] Is searchable (contains terms someone would query)?
- [ ] Makes sense without reading other patterns?
- [ ] No JSON/code in content (just prose)?

---

## Research Sources to Mine

### Source 1: Your Existing Composer Prompt
**Location:** `src/editor/composers/v2.py` - `CLIP_COMPOSER_SYSTEM_PROMPT`

**What to extract:**
- Energy interpretation rules (how kinetic differs from elegant)
- Spacing formulas (text positioning math)
- Anti-patterns (edge bleed, front-loading)
- Layer composition principles (4-6 layers for richness)

**How to extract:**
```
Read the prompt → Find actionable rules → Rewrite as self-contained patterns
```

### Source 2: Failed Renders Analysis
**What to do:**
1. Look at renders that didn't work well
2. Identify what went wrong (text overlap, timing issues, etc.)
3. Document as anti-patterns with specific fixes

### Source 3: Successful StreamLine Videos
**What to do:**
1. Take your best renders
2. Reverse-engineer the layer specs
3. Document what made them work

**Example pattern from success:**
```
"FocusFlow Purple Hero Success Pattern: Deep purple background (#1e1b4b) 
with cream text (#faf5ef) creates 12.5:1 contrast ratio, ensuring readability. 
Center-aligned text at x:50 y:70 with fontSize:90 avoids edge bleed. Staggered 
reveals (8-frame gaps) with slide_right animations. This specific combination 
generated 127 upvotes on Product Hunt first day. The contrast ratio is critical 
- anything below 7:1 feels washed out on mobile. Font weight 800 needed for 
cream on dark purple (600 looks weak). Based on FocusFlow launch January 2025."
```

### Source 4: Product Hunt Video Analysis
**Use Deep Research feature with this prompt:**
```
Analyze top 50 Product Hunt videos from 2024-2025. Extract:
- Common timing patterns (when do text reveals happen?)
- Animation combinations that appear repeatedly
- Layout strategies for different content types
- Color contrast ratios that work
- What separates 100+ upvote videos from <50 upvote videos

For each finding, include specific numbers and examples.
```

### Source 5: Remotion Community Examples
**Sources:**
- Remotion showcase: https://remotion.dev/showcase
- Remotion templates repo
- Community Discord examples

**What to extract:** Techniques you can adapt to StreamLine

---

## Pattern Categories You Need (Minimum)

### Energy Techniques (5-7 patterns, one per energy type)
- [ ] Kinetic energy execution
- [ ] Elegant energy execution  
- [ ] Calm/meditative energy execution
- [ ] Bold/aggressive energy execution
- [ ] Creative/playful energy execution

### Layout Patterns (8-10 patterns)
- [ ] Vertical stack (portrait screenshot + text)
- [ ] Horizontal split (text left, image right)
- [ ] Centered hero (single dominant element)
- [ ] Text-only composition
- [ ] Dual screenshot showcase
- [ ] Feature callout layout
- [ ] CTA-focused layout
- [ ] Diagonal composition

### Timing Patterns (5-7 patterns)
- [ ] 5-second clip temporal distribution
- [ ] 3-second clip temporal distribution  
- [ ] 2-second clip temporal distribution
- [ ] Staggered reveal cascade
- [ ] Front-loaded intro (when appropriate)
- [ ] Extended hold with motion

### Animation Combos (8-12 patterns)
- [ ] Zoom + drift background
- [ ] Pan + fade text
- [ ] Scale + stagger reveals
- [ ] Multi-phase motion
- [ ] Cross-layer coordination

### Anti-Patterns (10-15 patterns)
- [ ] Edge bleed (left/right/top/bottom)
- [ ] Text overlap errors
- [ ] Front-loading reveals
- [ ] Static dead time
- [ ] Excessive motion
- [ ] Poor contrast
- [ ] Misaligned energy (kinetic timing with calm directive)

### Calculations (5-8 patterns)
- [ ] Text spacing vertical
- [ ] Safe x-position for text
- [ ] Image scaling for portraits
- [ ] Image scaling for landscape
- [ ] Timeline duration calculation

**Total target: 50-80 patterns for robust knowledge base**

---

## Research Workflow Example

**Step 1: Extract from composer prompt (20 min)**
```bash
# Open src/editor/composers/v2.py
# Find all rules/formulas/examples
# Convert each to a pattern following the formula
```

**Step 2: Analyze your renders (30 min)**
```bash
# Review /Users/tk/Desktop/productvideo/output/
# Pick best 5 renders
# Document what techniques they used
# Pick worst 3 renders  
# Document what went wrong as anti-patterns
```

**Step 3: Deep research (1-2 hours)**
```
Use Claude with Deep Research:
"Analyze Product Hunt top videos for common execution patterns..."

Review results, extract 15-20 patterns
```

**Step 4: Format & ingest (20 min)**
```bash
# Add all patterns to JSON
# Run dry-run
python ingest_knowledge.py my_patterns.json --dry-run

# Ingest
python ingest_knowledge.py my_patterns.json

# Test
python ingest_knowledge.py my_patterns.json --test "kinetic stagger"
```

---

## Example Pattern Set (Complete)

Here's what 10 diverse patterns look like:

```json
{
  "namespace": "remotion_execution_patterns",
  "patterns": [
    // Energy technique
    {
      "id": "kinetic_energy_execution",
      "content": "Kinetic Energy Video Execution: Fast-paced confident tech energy requiring quick animations (10-15 frame enters), tight stagger gaps (5-10 frames between elements), and continuous motion throughout. Use slide, scale, stagger text animations with feel:\"snappy\". Image transforms should be noticeable (zoom 1.0→1.08, pan 15-20%). Background elements add motion: orbs, animated gradients, or grid patterns. Color contrast should be high (dark backgrounds with bright text). Typography: Bold weights (700-800), tight letter spacing (-0.02em to -0.03em). Spread reveals across first 60% of duration (90 frames in 150-frame clip), then sustain motion until end. Never let motion stop - if text reveals complete, background and images should still drift/zoom. Timing reference: Primary elements frames 10-40, mid-clip accent frame 55-70, all layers active with transforms 0-150. This energy drives Product Hunt, SaaS demos, tech launches. Avoid: Soft fades, gentle timing, pastel colors (feels weak). Based on top 50 Product Hunt launches 2024-2025.",
      "metadata": {"type": "energy_technique", "source": "streamline_composer_v2"},
      "relations": [
        {"to_id": "kinetic_staggered_reveals", "relation_type": "implements"},
        {"to_id": "temporal_distribution_5s", "relation_type": "uses"}
      ]
    },
    
    // Layout
    {
      "id": "horizontal_split_layout",
      "content": "Horizontal Split Layout (Text + Image): Divide canvas into left (text) and right (image) sections. Text positioned x:25-30 (left side, safe from edge bleed), image positioned x:70-75 (right side). For left-aligned text, calculate safe x using fontSize formula: x_min = 12 + (fontSize * 0.6 / 1920 * 100). Typical setup: Text fontSize:80-100 at x:28, image scale:0.5-0.6 at x:72. Both should be vertically centered (y:45-50) or use rule-of-thirds (y:38 and y:58). Add connecting element like vertical line at x:50 (optional, elegant energy only). Animation: Text slides from left (x:-10→28), image slides from right (x:110→72), simultaneous entrance frames 10-25. Works for: feature explanations, comparison layouts, desktop app demos. Stagger text layers within left section for richness: headline at x:28 y:40, subtext at x:28 y:58. Common mistake: Placing both at x:50 (no longer a split, just stacked). Image should be landscape or square for this layout, not portrait. Energy fit: kinetic/bold. Avoid for calm energy (too structured).",
      "metadata": {"type": "layout", "source": "layout_patterns_research"},
      "relations": [
        {"to_id": "left_aligned_edge_bleed", "relation_type": "avoids"},
        {"to_id": "vertical_stack_layout", "relation_type": "alternative_to"}
      ]
    },
    
    // Timing
    {
      "id": "quick_cta_timing",
      "content": "Quick CTA Clip Timing (2 seconds): CTAs and action prompts should be punchy 2-second clips (60 frames at 30fps). Structure: Background appears frame 0-8, text reveals frame 10-25 (15-frame entrance), holds frame 25-60. Use large fontSize (100-140) with bold weight (800). Animation should be immediate and confident: scale, slide_up, or pop with feel:\"snappy\". No secondary elements needed - single powerful message. Position center-screen (x:50 y:48-52). Colors: High contrast, use accent colors from brand palette. This short duration maintains momentum without dragging. Longer CTAs (3-4s) feel indecisive. Common mistake: 1.5 second CTAs (45 frames) don't give enough hold time - viewers miss it. 2 seconds is the sweet spot: 25 frames to reveal, 35 frames to hold. Place CTAs at: video end (final call), mid-video transition (soft CTA), after key feature demo. Energy: Works for all energies but adjust animation (kinetic: slide_up, elegant: fade, bold: pop). Based on conversion optimization tests showing 2s CTAs outperform 1.5s and 3s variants.",
      "metadata": {"type": "timing", "source": "cta_optimization_tests"},
      "relations": [
        {"to_id": "text_only_composition", "relation_type": "applies_to"}
      ]
    },
    
    // Anti-pattern
    {
      "id": "excessive_orb_motion",
      "content": "Excessive Background Orb Motion: Using too many animated orbs (7+) or high-speed drift creates visual chaos and distracts from primary content. Orbs should be subtle depth elements, not the focus. Safe values: 3-5 orbs maximum, slow drift speed, 30-50% opacity. Orbs work for kinetic/creative energy but overwhelm elegant/calm. This mistake appears when composer over-interprets \"add motion\" directive. Symptoms: Viewer eyes dart around, primary content feels obscured, low conversion rates. Fix: Reduce to 3 orbs, slow drift to 0.5x speed, lower opacity to 40%, or remove entirely for elegant energy. Alternative: Replace orbs with subtle gradient angle shift (135→145 over clip duration) for motion without distraction. Rule: Background motion should enhance, not compete with, foreground content. Test: Cover the orbs - does the composition still work? If removing orbs dramatically improves clarity, you had too many. Common in first-time kinetic energy compositions. Based on A/B tests showing 3-orb versions outperform 8-orb versions by 41% in click-through rates.",
      "metadata": {"type": "antipattern", "source": "ab_test_results_2024"},
      "relations": [
        {"to_id": "zoom_drift_combo", "relation_type": "contradicts"}
      ]
    },
    
    // Calculation
    {
      "id": "image_vertical_extent_calculation",
      "content": "Image Vertical Extent Calculation: Calculate how much vertical space a scaled image occupies to prevent text overlap. Formula: occupiedHeight = scale * imageNaturalHeight, then percentage = (occupiedHeight / 1080) * 100, centered around y position. Example: Portrait image 1170×2532 at y:35 scale:0.7: Natural height after scale = 2532 * 0.7 = 1772px. Scaled to fit 1080 canvas ≈ 456px actual height. Percentage: (456 / 1080) * 100 = 42.2%. Centered at y:35 means occupies y:13.9 to y:56.1. Therefore text must start at y:66 minimum (56.1 + 10% gap). For landscape images: Natural 1920×1080 at scale:0.6 = 648px wide, 388px tall = 36% height. Always calculate before placing text below images. Common mistake: Assuming y:35 image leaves room at y:70 for text (true for landscape, false for portrait). This prevents the \"text floating on image\" error that ruins compositions. Apply to: vertical stack layouts, centered hero with caption, any image-text combination.",
      "metadata": {"type": "calculation", "source": "spacing_math_guide"},
      "relations": [
        {"to_id": "vertical_stack_layout", "relation_type": "required_by"},
        {"to_id": "text_spacing_calculation", "relation_type": "related_to"}
      ]
    },
    
    // Animation combo
    {
      "id": "multi_phase_text_motion",
      "content": "Multi-Phase Text Motion (Enter + Continuous): Combine entrance animation with subtle continuous motion for premium feel. Phase 1 (frames 0-20): Text slides/fades into position. Phase 2 (frames 20-150): Subtle drift or scale pulse continues. Implementation: Use slide_right enterDuration:15 for entrance, then add continuous transform with gentle motion (translateY oscillation ±2px over 60 frames, or scale pulse 1.0→1.02→1.0). This prevents text from feeling \"locked\" after entrance. The continuous motion is barely perceptible but adds life. Timing: Entrance duration 15-20 frames (kinetic) or 20-25 frames (elegant), then continuous subtle motion throughout remaining duration. Works for: premium products, hero headlines, primary messages. Avoid: Supporting text or small fontSize (motion too subtle to notice, wasted computation). Apply continuous motion only to 1-2 key elements per clip, not everything (becomes busy). Technically: Entrance is animation.enter, continuous motion requires transform or additional animation layers. This technique appears in high-end fashion and luxury product videos, rarely in tech/SaaS (too subtle for kinetic energy).",
      "metadata": {"type": "animation_combo", "source": "premium_video_analysis"},
      "relations": [
        {"to_id": "elegant_fade_timing", "relation_type": "works_with"}
      ]
    }
  ]
}
```

---

## Relation Types Reference

| Relation Type | Meaning | Example |
|---------------|---------|---------|
| `requires` | Pattern A needs pattern B | Layout requires spacing calculation |
| `works_with` | Pattern A complements pattern B | Zoom works with staggered text |
| `contradicts` | Pattern A conflicts with pattern B | Anti-pattern contradicts best practice |
| `implements` | Pattern A is a specific case of pattern B | Stagger implements temporal distribution |
| `applies_to` | Pattern A is used in pattern B context | Text animation applies to text-only clips |
| `avoids` | Pattern A prevents pattern B | Good layout avoids edge bleed |
| `alternative_to` | Pattern A is substitute for pattern B | Gradient alternative to orbs |
| `contrasts_with` | Pattern A differs from pattern B | Elegant contrasts with kinetic |
| `related_to` | General relationship | Vertical calc related to horizontal calc |

---

## How to Expand the Knowledge Base

### Week 1: Bootstrap (50 patterns)
1. Extract from composer prompt (15 patterns)
2. Document common mistakes (10 anti-patterns)
3. Add basic layouts (8 patterns)
4. Add timing patterns (7 patterns)
5. Add calculations (5 patterns)
6. Add energy techniques (5 patterns)

### Week 2: Refine (20 more patterns)
1. Analyze your best renders (5 patterns from success)
2. Analyze failures (5 anti-patterns)
3. Deep research Product Hunt (10 patterns)

### Week 3: Specialize (20 more patterns)
1. Industry-specific patterns (SaaS, fashion, wellness)
2. Advanced animation combos
3. Edge cases and exceptions

### Ongoing: Learn from production
- Every good render → Extract pattern
- Every mistake → Document anti-pattern
- Every user request that breaks patterns → Add new pattern

---

## Testing Your Knowledge Base

After ingesting, test with queries your composer would actually make:

```bash
# Query 1: Energy-based
python ingest_knowledge.py patterns.json --test "kinetic energy text animation" --match-count 5

# Query 2: Layout-based  
python ingest_knowledge.py patterns.json --test "portrait screenshot vertical layout"

# Query 3: Problem-solving
python ingest_knowledge.py patterns.json --test "text overlapping image fix"

# Query 4: Combination
python ingest_knowledge.py patterns.json --test "elegant fade timing spacing"
```

**Good results:** Returns 3-5 highly relevant patterns
**Bad results:** Returns generic or off-topic patterns → Refine content to be more searchable

---

## Pro Tips

1. **Use your own voice** - Don't copy scaffold examples verbatim, adapt to Remotion/StreamLine specifics

2. **Include numbers INLINE** - Don't reference external tables or "see formula above"

3. **Write for search** - Include terms someone would query naturally

4. **One pattern = one idea** - Don't try to cover 3 techniques in one pattern (split into 3)

5. **Relations matter** - Graph traversal finds related patterns automatically during search

6. **Start small, test, expand** - 20 good patterns > 100 mediocre ones

7. **Document your own discoveries** - Your StreamLine-specific learnings are more valuable than generic Remotion tips

---

## Next Steps

1. **Setup database:**
   ```bash
   # Copy SQL, run in Supabase SQL Editor
   cat setup_rag_db.sql
   ```

2. **Start with composer prompt extraction:**
   - Read `src/editor/composers/v2.py`
   - Extract 10-15 patterns
   - Add to JSON

3. **Ingest & test:**
   ```bash
   python ingest_knowledge.py my_patterns.json
   ```

4. **Integrate with composer:**
   - Add RAG query to `compose_single_clip_node`
   - Test with real composition

5. **Iterate:**
   - Use system, find gaps
   - Add patterns for missing cases
   - Build up to 50-80 patterns over time
