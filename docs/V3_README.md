# StreamLine Video Pipeline V3

## What's New in V3

### 1. Design System Separation

**Before (V2):** Planner repeated colors, typography, and style rules in every `composer_notes`. Composer had to parse this from prose.

**After (V3):** Planner calls `create_design_system()` ONCE. This creates a unified design system stored in `video_projects.design_system_text`. Every clip automatically receives it.

```
V2 Flow:
┌─────────────────────────────────────────────────────────────┐
│ Planner → composer_notes (with colors, fonts, energy, etc) │
│ Planner → composer_notes (with colors, fonts, energy, etc) │
│ Planner → composer_notes (with colors, fonts, energy, etc) │
└─────────────────────────────────────────────────────────────┘

V3 Flow:
┌─────────────────────────────────────────────────────────────┐
│ Planner → create_design_system() [ONCE]                    │
│         → create_clip_task() [content-focused notes only]  │
│         → create_clip_task() [content-focused notes only]  │
│         → create_clip_task() [content-focused notes only]  │
│                                                             │
│ Composer receives:                                          │
│   • design_system_text (colors, fonts, feel)               │
│   • composer_notes (content strategy, energy)               │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- No style drift across clips
- Smaller `composer_notes` (content-focused only)
- Single source of truth for visual identity

---

### 2. Real Pixel Validation System

**Before (V2):** Validation used character-count estimation for text width. Often wrong.

**After (V3):** New `measure-real.ts` script computes actual bounding boxes, spacing matrices, and contrast ratios.

#### New Validation Output Format

```
LAYOUT:
  [0] background
  [1] image     650×840 @ (1200, 540)
  [2] text      380×52  @ (450, 320)  'Transform Your...' 64px
  [3] text      280×36  @ (450, 400)  'AI-powered ins...' 24px ⚠️2lines

SPACING:
  [1]↔[2]:  120px  ✓
  [2]↔[3]:   28px  ⚠️ min 40px

CONTRAST:
  [2]: 8.2 ✓
  [3]: 1.8 ❌ (#666666 on #5E73F2)

────────────────────────────────────────
ISSUES:
  ⚠️ [2]↔[3] gap 28px (min 40px)
  ❌ [3] contrast 1.8 (need 4.5) — #666666 on #5E73F2
  ⚠️ [3] wraps to 2 lines (no maxWidth)
```

**Key Improvements:**
- One line per layer (scannable at a glance)
- Spacing matrix shows every pair with gap + status
- Clear symbols: `❌` = error, `⚠️` = warning, `✓` = pass
- Contrast calculated from actual background colors under text
- No verbose explanations, just data

---

## V3 Architecture

### Planner (v3.py)

```python
# Step 1: Query RAG for planning patterns
query_video_planning_patterns("narrative arc tempo")

# Step 2: Create unified design system (REQUIRED, ONCE)
create_design_system("""
Style: KINETIC_PRODUCT_HUNT light mode

Colors:
  Background: #F5F8FA
  Headline: #111827
  Subtext: #4B5563
  Accent: #7C3AED

Typography:
  Family: Inter
  Headline: 72-100px, weight 700-800
  Subtext: 36-48px, weight 400-500

Animation: snappy feel, staggered reveals
""")

# Step 3: Create clips with content-focused notes
create_clip_task(
    asset_path="screen1.png",
    start_time_s=0,
    duration_s=4,
    composer_notes="""
    Clip function: hook
    Content: "Transform Your Workflow" headline, "AI-powered insights" subtext
    Asset: iPhone screenshot at 1170×2532, show right side
    Energy: KINETIC - punchy entrance, confident hold
    """
)
```

### Composer (v3.py)

Composer receives TWO separate inputs:

```python
# From design_system_text (project-wide):
Style: KINETIC_PRODUCT_HUNT light mode
Colors: Background #F5F8FA, Headline #111827, ...
Typography: Inter, Headline 72-100px weight 700-800, ...

# From composer_notes (clip-specific):
Clip function: hook
Content: "Transform Your Workflow" headline
Energy: KINETIC - punchy entrance
```

**Composer's Job:**
- Use colors/fonts from `design_system_text`
- Use content strategy from `composer_notes`
- Query RAG for layout/spacing/timing execution details
- Draft → Validate → Fix → Submit

---

## Files Changed in V3

| File | Change |
|------|--------|
| `src/editor/planners/v3.py` | New `create_design_system` tool usage |
| `src/editor/composers/v3.py` | Receives `design_system_text` + `composer_notes` |
| `src/tools/editor_tools.py` | Added `create_design_system()` tool |
| `src/tools/draft_tools.py` | Rewritten with concise validation output |
| `remotion/scripts/measure-real.ts` | NEW - Real pixel measurement |
| `remotion/scripts/measure-layers.js` | Simplified as fallback |

---

## Database Schema Changes

```sql
-- video_projects table
ALTER TABLE video_projects ADD COLUMN design_system_text TEXT;
```

The `design_system_text` column stores the unified visual style that all clips reference.

---

## Workflow Comparison

### V2 Workflow
```
Planner:
  1. Query RAG
  2. Create clips (each with full style specs in composer_notes)
  3. Finalize

Composer:
  1. Parse style from composer_notes
  2. Query RAG for execution
  3. Draft → Validate → Submit
```

### V3 Workflow
```
Planner:
  1. Query RAG
  2. Create design system (ONCE)
  3. Create clips (content-focused notes only)
  4. Finalize

Composer:
  1. Read design_system_text (automatic)
  2. Read composer_notes (content strategy)
  3. Query RAG for execution
  4. Draft → Validate (real pixels) → Fix → Submit
```

---

## Test Command

```bash
cd /Users/tk/Desktop/productvideo/src && python test_composer_v2.py
```

---

## Debugging Validation Failures

When validation fails, check:

1. **Did composer query relevant RAG patterns?** (check log's rag_queries)
2. **Did RAG return useful results?** (check results in log)
3. **Did composer follow the numbers?** (compare RAG guidance vs actual layer positions)

If RAG returned good guidance but composer ignored → execution gap → strengthen composer prompt.
If RAG returned irrelevant results → knowledge gap → add better RAG patterns.
