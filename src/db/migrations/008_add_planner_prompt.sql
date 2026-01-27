-- Migration 008: Add planner_prompt_sent to video_projects
-- Stores the complete prompt sent to the planner agent for debugging and optimization

ALTER TABLE video_projects
ADD COLUMN IF NOT EXISTS planner_prompt_sent TEXT;

COMMENT ON COLUMN video_projects.planner_prompt_sent IS
'Complete prompt sent to the edit planner agent, including system prompt and user context.';
