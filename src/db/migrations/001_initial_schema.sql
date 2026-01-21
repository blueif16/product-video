-- Video project: THE complete record of a production job
-- Status enum: 'analyzed', 'capturing', 'aggregated'
create table video_projects (
    id uuid default gen_random_uuid() primary key,
    user_input text not null,
    project_path text,
    app_bundle_id text,
    analysis_summary text,
    status text default 'analyzed',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Capture tasks: individual screenshot/recording jobs
-- Status enum: 'pending', 'success', 'failed'
create table capture_tasks (
    id uuid default gen_random_uuid() primary key,
    app_bundle_id text not null,
    task_description text not null,
    status text default 'pending',
    attempt_count int default 0,
    capture_type text not null,
    asset_path text,
    validation_notes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
