-- Migration 005: Add asset_url to clip_tasks
-- Enables cloud-first architecture for editor phase

ALTER TABLE clip_tasks 
ADD COLUMN IF NOT EXISTS asset_url TEXT;

COMMENT ON COLUMN clip_tasks.asset_url IS 
'Cloud storage URL for the asset. Preferred over asset_path for Remotion rendering.';

-- Index for queries filtering by URL presence
CREATE INDEX IF NOT EXISTS idx_clip_tasks_asset_url
ON clip_tasks(video_project_id) 
WHERE asset_url IS NOT NULL;
