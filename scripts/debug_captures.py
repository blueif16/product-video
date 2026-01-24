#!/usr/bin/env python3
"""
Debug script to check what was actually captured in the last video project
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.supabase_client import get_supabase

def main():
    client = get_supabase()
    
    # Get the most recent video project
    projects = client.table('video_projects').select('*').order('created_at', desc=True).limit(1).execute()
    
    if not projects.data:
        print("No video projects found")
        return
    
    project = projects.data[0]
    project_id = project['id']
    
    print(f"Project ID: {project_id}")
    print(f"Status: {project['status']}")
    print(f"User Input: {project['user_input'][:100]}...")
    print()
    
    # Get all capture tasks
    tasks = client.table('capture_tasks').select('*').eq('video_project_id', project_id).execute()
    
    print(f"Total capture tasks: {len(tasks.data)}")
    print("=" * 80)
    
    for i, task in enumerate(tasks.data, 1):
        print(f"\n[Task {i}]")
        print(f"  Type: {task['capture_type']}")
        print(f"  Description: {task['task_description'][:60]}...")
        print(f"  Status: {task['status']}")
        print(f"  Asset Path: {task.get('asset_path', 'None')}")
        if task.get('validation_notes'):
            print(f"  Validation: {task['validation_notes'][:80]}...")
    
    # Check if there are any files in the asset paths
    print("\n" + "=" * 80)
    print("Checking actual files:")
    print("=" * 80)
    
    unique_assets = set()
    for task in tasks.data:
        if task.get('asset_path'):
            unique_assets.add(task['asset_path'])
    
    print(f"\nUnique asset paths in database: {len(unique_assets)}")
    for path in sorted(unique_assets):
        exists = os.path.exists(path) if path else False
        print(f"  {'✓' if exists else '✗'} {path}")

if __name__ == '__main__':
    main()
