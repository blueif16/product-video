-- Add final_video_path column to video_projects table
-- This stores the cloud URL of the final rendered video

ALTER TABLE video_projects
ADD COLUMN IF NOT EXISTS final_video_path text;

COMMENT ON COLUMN video_projects.final_video_path IS 'Cloud storage URL of the final rendered video';
