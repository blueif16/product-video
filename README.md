# Product Video Pipeline

AI-powered product video generation for Product Hunt launches and SaaS marketing.

**You describe your app. It captures the assets.**

## What This Does

```
"My app FocusFlow is a minimalist task manager with smooth animations. 
 I want a 30-second energetic promo for Product Hunt. 
 Project is at ~/Code/FocusFlow/FocusFlow.xcodeproj"
         ↓
   [Analyzes code, captures screens]
         ↓
   Assets ready for editing
```

## Architecture

### Core Principle: Pure LLM Judgment, Zero Parsing

Every decision is made by an LLM with appropriate expertise. No regex, no keyword matching, no hardcoded formulas.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PIPELINE FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  intake ──────→ Traffic cop. Validates project path exists.                │
│                 Knows NOTHING about video production.                       │
│                 Tool: confirm_project(path, bundle_id)                      │
│                                                                             │
│      ↓                                                                      │
│                                                                             │
│  analyze ─────→ Domain expert. OWNS video strategy.                        │
│                 Reads user request + explores codebase.                     │
│                 Decides: what to capture, how many, why.                    │
│                 Writes analysis_summary (full thinking).                    │
│                 Tools: create_capture_task(), finalize_analysis()           │
│                                                                             │
│      ↓                                                                      │
│                                                                             │
│  capture ─────→ Parallel execution. One agent per task.                    │
│  (fan-out)      Launches app, navigates, captures, validates.              │
│                 Tool: report_capture_result(success, path, notes)           │
│                                                                             │
│      ↓                                                                      │
│                                                                             │
│  aggregate ───→ Collects results, updates status.                          │
│                 Next phase reads full context from DB.                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What "Zero Parsing" Means

**Old (bad):**
```python
# Extract duration from text
match = re.search(r'(\d+)\s*seconds?', user_input)
duration = int(match.group(1))

# Hardcoded vibe multipliers
asset_count = base_count * {"energetic": 1.3, "calm": 0.8}[vibe]
```

**New (good):**
```python
# Analyzer reads user request and codebase, then decides
@tool
def finalize_analysis(analysis_summary: str):
    """
    Your complete strategy including:
    - What user wants (your interpretation)
    - Why these captures (your reasoning)  
    - How they fit together (your plan)
    """
```

The analyzer's full thinking flows to the next phase as context, not lossy extracted fields.

## Project Structure

```
src/
├── config.py                 # API keys, paths, settings
├── main.py                   # Entry point
├── orchestrator/
│   ├── __init__.py           # Exports run_pipeline
│   ├── state.py              # PipelineState, CaptureTaskState
│   ├── intake.py             # Path validation (dumb)
│   ├── analyzer.py           # Video strategy (expert)
│   ├── capturer.py           # Asset capture (executor)
│   ├── aggregate.py          # Result collection
│   └── graph.py              # LangGraph wiring
├── tools/
│   ├── bash_tools.py         # Shell commands
│   ├── capture_tools.py      # xcrun simctl wrappers
│   └── validation_tool.py    # Multimodal validation
└── db/
    ├── migrations/
    │   └── 001_initial_schema.sql
    └── supabase_client.py
```

## Database Schema

Two tables. That's it.

```sql
-- Video project: THE complete record of a production job
-- Status: 'analyzed' → 'capturing' → 'aggregated'
create table video_projects (
    id uuid primary key,
    user_input text not null,        -- Original request (flows through)
    project_path text,
    app_bundle_id text,
    analysis_summary text,           -- Analyzer's full thinking
    status text default 'analyzed',
    created_at timestamptz,
    updated_at timestamptz
);

-- Capture tasks: individual screenshot/recording jobs
-- Status: 'pending' → 'success' | 'failed'
create table capture_tasks (
    id uuid primary key,
    app_bundle_id text not null,
    task_description text not null,  -- Full instructions
    status text default 'pending',
    attempt_count int default 0,
    capture_type text not null,      -- 'screenshot' | 'recording'
    asset_path text,
    validation_notes text,
    created_at timestamptz,
    updated_at timestamptz
);
```

See `src/db/migrations/001_initial_schema.sql` for full DDL.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in API keys
```

Run the migration in Supabase, then:

```bash
python -m src.main
```

Describe your project naturally:

```
> My app FocusFlow is a minimalist iOS task manager with beautiful animations.
  Main features: quick task entry, swipe actions, focus timer.
  I want a 30-second energetic promo for Product Hunt.
  Project: ~/Code/FocusFlow/FocusFlow.xcodeproj
```

## Environment Variables

```bash
# .env
GEMINI_API_KEY=...           # For LLM (analysis, validation)
SUPABASE_URL=...             # Your Supabase project URL  
SUPABASE_KEY=...             # Secret key (sb_secret_... or service_role)
```

## Status Flow

```
analyzed    → Tasks created, ready to capture
capturing   → Capturers dispatched, work in progress
aggregated  → Capture phase complete, assets ready
```

Query `capture_tasks` for per-task status:
- `pending` - Not yet attempted
- `success` - Asset captured and validated
- `failed` - Capture failed after max attempts

## How Context Flows

```
User input: "30s energetic video for my focus app at ~/Code/FocusFlow"
                    ↓
         ┌─────────────────────┐
         │      INTAKE         │
         │ (just validates     │
         │  path exists)       │
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │     ANALYZER        │
         │                     │
         │ Reads: user_input   │
         │ Explores: codebase  │
         │ Thinks: "30s means  │
         │   ~12-15 shots,     │
         │   energetic = fast  │
         │   cuts, this app    │
         │   has 3 key anims"  │
         │                     │
         │ Creates: tasks      │
         │ Writes: analysis    │
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │   VIDEO_PROJECTS    │
         │                     │
         │ user_input: (raw)   │
         │ analysis_summary:   │
         │   (full thinking)   │
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │   FUTURE: EDITOR    │
         │                     │
         │ Reads: user_input   │
         │ Reads: analysis     │
         │ Reads: assets       │
         │                     │
         │ Makes editorial     │
         │ decisions with      │
         │ FULL CONTEXT        │
         └─────────────────────┘
```

## Design Principles

1. **Each agent has a specialty**
   - Intake: path validation (dumb)
   - Analyzer: video strategy (expert)
   - Capturer: execution (worker)
   - Editor (future): assembly (expert)

2. **Context flows through, not extracted fields**
   - Bad: `duration=30, vibe="energetic"`
   - Good: `analysis_summary` with full reasoning

3. **Every state change uses a tool call**
   - No parsing LLM output for success/failure
   - Agent calls `report_capture_result(success=True, ...)`

4. **Database is source of truth**
   - Tasks read from DB, not message parsing
   - Results written to DB, not inferred from text

5. **Human-in-the-loop via interrupt()**
   - Clean pauses when info missing
   - User answers, pipeline resumes

## Pipeline Phases

### Phase 1: Asset Capture ✅ (Current)

- Validate project path
- Analyze codebase + user intent
- Create capture tasks
- Execute captures in parallel
- Validate with multimodal LLM
- Store results

### Phase 2: Creative Generation (Planned)

- Generate music via Suno MCP
- Beat detection → timestamps
- Generate text animations (Puppeteer capture)
- Device frame overlays

### Phase 3: Assembly (Planned)

- DaVinci Resolve MCP
- Beat-synced timeline
- Fusion transforms (zoom, pan)
- Transitions, text overlays
- Final render

## Troubleshooting

**"No simulator booted"**
```bash
xcrun simctl boot "iPhone 15 Pro"
```

**"Path does not exist"**
- Check for typos
- Expand `~` manually if needed
- Must be `.xcodeproj` or project directory

**"Validation keeps failing"**
Check `validation_notes` in `capture_tasks` table:
- Loading spinners → add longer waits
- Empty states → need test data
- System dialogs → dismiss permissions first
