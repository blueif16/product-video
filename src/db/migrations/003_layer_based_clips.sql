-- Migration: Layer-Based Clips
-- 
-- This migration transforms the editor from parallel clip+text tracks
-- to a unified layer-based composition model.
--
-- BEFORE: clip_tasks (images) + text_tasks (text overlays) → separate tracks
-- AFTER:  clip_tasks with layers[] → each "moment" is self-contained

-- ─────────────────────────────────────────────────────────────
-- Step 1: Drop text_tasks table (no longer needed)
-- ─────────────────────────────────────────────────────────────

-- First drop any foreign key constraints or indexes
drop trigger if exists text_tasks_updated_at on text_tasks;
drop index if exists idx_text_tasks_project;
drop index if exists idx_text_tasks_status;

-- Drop the table
drop table if exists text_tasks;

-- ─────────────────────────────────────────────────────────────
-- Step 2: Add generated_assets table (for AI-enhanced images)
-- ─────────────────────────────────────────────────────────────

create table if not exists generated_assets (
    id uuid primary key default gen_random_uuid(),
    video_project_id uuid not null references video_projects(id) on delete cascade,
    clip_task_id uuid references clip_tasks(id) on delete cascade,
    
    -- Generation details
    source_asset_path text,              -- Original asset this was generated from (if any)
    prompt text not null,                -- The generation prompt
    asset_path text,                     -- Where the generated asset is stored
    asset_url text,                      -- CDN/signed URL for the asset
    
    -- Metadata
    generation_model text,               -- e.g., "gemini-3-pro-image-preview"
    generation_params jsonb,             -- Any additional params
    
    status text default 'pending',       -- 'pending' | 'generating' | 'success' | 'failed'
    error_message text,
    
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_generated_assets_project on generated_assets(video_project_id);
create index if not exists idx_generated_assets_clip on generated_assets(clip_task_id);

-- ─────────────────────────────────────────────────────────────
-- Step 3: Update clip_tasks to support new layer-based clip_spec
-- ─────────────────────────────────────────────────────────────

-- Add a column to store the new layer-based spec format
-- The existing clip_spec jsonb column will now store this structure:
-- 
-- {
--   "durationFrames": 60,
--   "layers": [
--     {
--       "type": "image",
--       "src": "screenshot.png",
--       "zIndex": 1,
--       "transform": {...},
--       "opacity": {"start": 1, "end": 1}
--     },
--     {
--       "type": "generated_image",
--       "src": "enhanced.png",
--       "generatedAssetId": "uuid",
--       "zIndex": 2,
--       "transform": {...},
--       "opacity": {"start": 0, "end": 1}
--     },
--     {
--       "type": "text",
--       "content": "FOCUS",
--       "zIndex": 3,
--       "style": {...},
--       "animation": {...},
--       "position": {...}
--     }
--   ],
--   "enterTransition": {...},
--   "exitTransition": {...},
--   "composerNotes": "..."
-- }

-- No schema change needed - clip_spec is already jsonb
-- Just documenting the new expected structure

comment on column clip_tasks.clip_spec is 
'Layer-based clip specification. Structure: {durationFrames, layers[], enterTransition?, exitTransition?, composerNotes}';

-- ─────────────────────────────────────────────────────────────
-- Step 4: Triggers for new table
-- ─────────────────────────────────────────────────────────────

create trigger generated_assets_updated_at
    before update on generated_assets
    for each row execute function update_updated_at();

-- ─────────────────────────────────────────────────────────────
-- Step 5: Update video_projects for new workflow
-- ─────────────────────────────────────────────────────────────

-- Add column for tracking generated assets count
alter table video_projects 
add column if not exists generated_asset_count int default 0;

-- ─────────────────────────────────────────────────────────────
-- Done!
-- ─────────────────────────────────────────────────────────────

-- Summary of changes:
-- 1. Dropped text_tasks table
-- 2. Added generated_assets table for AI-enhanced images
-- 3. Documented new clip_spec layer structure
-- 4. clip_tasks now represent "moments" with multiple layers
