-- Editor Phase Tables
-- Run after 001_initial_schema.sql
--
-- NOTE: text_tasks table was removed in the simplification.
-- Text overlays are now layers inside clip_tasks, not separate entities.

-- ─────────────────────────────────────────────────────────────
-- Clip Tasks: "Moments" in the video timeline
-- ─────────────────────────────────────────────────────────────
create table clip_tasks (
    id uuid primary key default gen_random_uuid(),
    video_project_id uuid not null references video_projects(id) on delete cascade,
    
    -- Asset reference (can be null for text-only moments)
    asset_id uuid references capture_tasks(id),
    asset_path text,
    
    -- Timeline position (planner decides)
    start_time_s float not null,
    duration_s float not null,
    
    -- The planner's creative vision - THIS IS THE KEY FIELD
    -- Rich creative direction, no rigid structure
    -- Example: "Zoom slowly to task counter, add 'FOCUS' text that types in,
    --           calm confident energy, crossfade to glowing AI version"
    composer_notes text not null,
    
    -- The composer's technical implementation (layer-based)
    -- Structure: {durationFrames, layers[], enterTransition?, exitTransition?, composerNotes}
    -- layers[] contains: background, image, text (no separate generated_image type)
    clip_spec jsonb,
    
    status text default 'pending',  -- 'pending' | 'composed' | 'failed'
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- ─────────────────────────────────────────────────────────────
-- Video Specs: Assembled timeline ready for Remotion
-- ─────────────────────────────────────────────────────────────
create table video_specs (
    id uuid primary key default gen_random_uuid(),
    video_project_id uuid not null references video_projects(id) on delete cascade,
    
    -- The complete VideoSpec JSON for Remotion
    spec jsonb not null,
    
    -- Versioning for iteration
    version int not null default 1,
    
    -- Render tracking
    render_status text default 'pending',  -- 'pending' | 'rendering' | 'complete' | 'failed'
    render_path text,
    render_error text,
    render_started_at timestamptz,
    render_completed_at timestamptz,
    
    created_at timestamptz default now(),
    
    unique(video_project_id, version)
);

-- ─────────────────────────────────────────────────────────────
-- Music Analyses: Post-render music generation (Phase 4)
-- ─────────────────────────────────────────────────────────────
create table music_analyses (
    id uuid primary key default gen_random_uuid(),
    video_project_id uuid not null references video_projects(id) on delete cascade,
    video_spec_id uuid references video_specs(id),
    
    -- Analysis of the rendered video
    pacing_curve jsonb,  -- Frame-by-frame pacing analysis
    
    -- Generated music
    music_prompt text,
    music_track_url text,
    beat_timestamps jsonb,  -- From librosa: [0.0, 0.5, 1.0, ...]
    
    -- Suggestions for re-alignment (optional optimization)
    recut_suggestions jsonb,  -- "Extend clip 3 by 5 frames to hit beat"
    
    status text default 'pending',
    created_at timestamptz default now()
);

-- ─────────────────────────────────────────────────────────────
-- Generated Assets: AI-enhanced images
-- ─────────────────────────────────────────────────────────────
-- These are just images with a src path. The clip_spec uses them
-- via "type": "image" (same as captured screenshots).
-- This table exists for tracking/debugging/regeneration.
create table generated_assets (
    id uuid primary key default gen_random_uuid(),
    video_project_id uuid not null references video_projects(id) on delete cascade,
    clip_task_id uuid references clip_tasks(id) on delete cascade,
    
    -- Generation details
    source_asset_path text,              -- Original asset this was generated from (if any)
    prompt text not null,                -- The generation prompt
    aspect_ratio text default '16:9',    -- 16:9, 9:16, 1:1, 4:3
    description text,                    -- Optional label (defaults to prompt summary)
    
    -- Output
    asset_path text,                     -- Local path to generated asset
    asset_url text,                      -- CDN/signed URL for the asset
    
    -- Metadata
    generation_model text,               -- e.g., "gemini-3-pro-image-preview"
    
    status text default 'pending',       -- 'pending' | 'generating' | 'success' | 'failed'
    error_message text,
    
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- ─────────────────────────────────────────────────────────────
-- Add editor status to video_projects
-- ─────────────────────────────────────────────────────────────
alter table video_projects 
add column if not exists editor_status text default null;
-- Values: null | 'planning' | 'composing' | 'assembled' | 'rendering' | 'rendered'

-- Add video_project_id to capture_tasks for proper relationship
alter table capture_tasks
add column if not exists video_project_id uuid references video_projects(id) on delete cascade;

-- ─────────────────────────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────────────────────────
create index if not exists idx_clip_tasks_project on clip_tasks(video_project_id);
create index if not exists idx_clip_tasks_status on clip_tasks(status);
create index if not exists idx_video_specs_project on video_specs(video_project_id);
create index if not exists idx_music_analyses_project on music_analyses(video_project_id);
create index if not exists idx_capture_tasks_project on capture_tasks(video_project_id);
create index if not exists idx_generated_assets_project on generated_assets(video_project_id);
create index if not exists idx_generated_assets_clip on generated_assets(clip_task_id);

-- ─────────────────────────────────────────────────────────────
-- Updated_at triggers
-- ─────────────────────────────────────────────────────────────
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger clip_tasks_updated_at
    before update on clip_tasks
    for each row execute function update_updated_at();

create trigger generated_assets_updated_at
    before update on generated_assets
    for each row execute function update_updated_at();
