-- ═══════════════════════════════════════════════════════════════════════════
-- Migration 004: Asset URLs and Unified Pipeline Support
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- Run this in Supabase SQL Editor to add support for:
-- 1. Cloud storage URLs for captured assets
-- 2. Upload-mode projects (skip capture phase)
-- 3. Better indexing for API queries
--
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Add cloud storage URL to capture_tasks
-- This stores the Supabase Storage public URL for frontend display
-- asset_path remains for local Remotion rendering
ALTER TABLE capture_tasks 
ADD COLUMN IF NOT EXISTS asset_url TEXT;

COMMENT ON COLUMN capture_tasks.asset_url IS 
'Supabase Storage public URL for frontend display. asset_path remains for local Remotion access.';

-- 2. Add cloud storage URL to generated_assets (for AI-generated images)
ALTER TABLE generated_assets
ADD COLUMN IF NOT EXISTS asset_url TEXT;

COMMENT ON COLUMN generated_assets.asset_url IS
'Supabase Storage public URL for AI-generated images.';

-- 3. Add source tracking to video_projects
-- Tracks whether assets came from capture or upload
ALTER TABLE video_projects
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'capture';

COMMENT ON COLUMN video_projects.source IS 
'How assets were obtained: capture | upload';

-- 4. Add pipeline_mode for unified graph routing
-- Determines which pipeline path to take
ALTER TABLE video_projects
ADD COLUMN IF NOT EXISTS pipeline_mode TEXT DEFAULT 'full';

COMMENT ON COLUMN video_projects.pipeline_mode IS 
'Which pipeline to run: full | editor_only | upload';

-- 5. Performance indexes for API queries
CREATE INDEX IF NOT EXISTS idx_capture_tasks_project_status 
ON capture_tasks(video_project_id, status);

CREATE INDEX IF NOT EXISTS idx_capture_tasks_project_url
ON capture_tasks(video_project_id) 
WHERE asset_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_video_projects_status 
ON video_projects(status);

CREATE INDEX IF NOT EXISTS idx_video_projects_source
ON video_projects(source);

-- 6. Update existing capture tasks to have status if null
UPDATE capture_tasks 
SET status = 'pending' 
WHERE status IS NULL;

-- 7. Ensure video_projects has updated_at trigger
-- (may already exist from earlier migrations)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_video_projects_updated_at'
    ) THEN
        CREATE TRIGGER update_video_projects_updated_at
            BEFORE UPDATE ON video_projects
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════
-- Verification Queries (run after migration to verify)
-- ═══════════════════════════════════════════════════════════════════════════
/*
-- Check capture_tasks columns
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'capture_tasks'
ORDER BY ordinal_position;

-- Check video_projects columns  
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'video_projects'
ORDER BY ordinal_position;

-- Check indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename IN ('capture_tasks', 'video_projects');
*/
