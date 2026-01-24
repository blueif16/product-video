-- ═══════════════════════════════════════════════════════════════════════════
-- Migration 006: Make app_bundle_id nullable for upload mode
-- ═══════════════════════════════════════════════════════════════════════════
--
-- For upload-mode projects, we don't have an app to capture from,
-- so app_bundle_id should be nullable.
--
-- ═══════════════════════════════════════════════════════════════════════════

-- Make app_bundle_id nullable in capture_tasks
ALTER TABLE capture_tasks
ALTER COLUMN app_bundle_id DROP NOT NULL;

COMMENT ON COLUMN capture_tasks.app_bundle_id IS
'App bundle ID for capture mode. NULL for upload mode.';

-- ═══════════════════════════════════════════════════════════════════════════
-- Verification
-- ═══════════════════════════════════════════════════════════════════════════
/*
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_name = 'capture_tasks' AND column_name = 'app_bundle_id';
*/
