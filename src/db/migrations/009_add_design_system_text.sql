-- Migration 009: Add design_system_text to video_projects
-- Stores the unified visual style (colors, typography, animation feel) for all clips

ALTER TABLE video_projects
ADD COLUMN IF NOT EXISTS design_system_text TEXT;

COMMENT ON COLUMN video_projects.design_system_text IS
'Unified design system for the video including color palette, typography rules, and animation feel. Created by planner, read by all composers.';
