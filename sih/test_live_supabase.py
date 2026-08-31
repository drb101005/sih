import os
import sys
from pathlib import Path

# Add current dir to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from database.config import settings
from database.client import get_supabase_client, is_supabase_connected
from database.repositories import CorridorRepository, TaskRepository, BlockRepository

print("=" * 60)
print("SUPABASE LIVE CONNECTION TEST")
print("=" * 60)
print(f"SUPABASE_URL: {settings.SUPABASE_URL}")
print(f"SUPABASE_KEY prefix: {settings.SUPABASE_KEY[:12]}...")

client = get_supabase_client()
connected = is_supabase_connected()
print(f"Supabase Client Initialized: {connected}")

if not connected:
    print("\n[ERROR] Failed to connect to Supabase. Check your URL and Key.")
    sys.exit(1)

# 1. Test Corridors Table
try:
    corridor_repo = CorridorRepository()
    corridors = corridor_repo.get_all()
    print(f"\n[1] 'corridors' table: Successfully queried {len(corridors)} records from Supabase.")
    if corridors:
        print(f"    Sample corridor: {corridors[0].get('corridor_id')} - {corridors[0].get('corridor_name', 'N/A')} ({corridors[0].get('status', 'N/A')})")
except Exception as e:
    print(f"\n[!] Error querying 'corridors': {e}")

# 2. Test Maintenance Tasks Table
try:
    task_repo = TaskRepository()
    tasks = task_repo.get_all(limit=5)
    print(f"\n[2] 'maintenance_tasks' table: Successfully queried {len(tasks)} sample records.")
    if tasks:
        print(f"    Sample task: {tasks[0].get('task_id')} | corridor: {tasks[0].get('corridor_id')} | department: {tasks[0].get('department')}")
except Exception as e:
    print(f"\n[!] Error querying 'maintenance_tasks': {e}")

# 3. Test Blocks Table
try:
    block_repo = BlockRepository()
    blocks = block_repo.get_available_blocks(limit=5)
    print(f"\n[3] 'blocks' table: Successfully queried {len(blocks)} sample available blocks.")
    if blocks:
        print(f"    Sample block: {blocks[0].get('block_id')} | corridor: {blocks[0].get('corridor_id')} | availability: {blocks[0].get('availability')}")
except Exception as e:
    print(f"\n[!] Error querying 'blocks': {e}")

print("\n" + "=" * 60)
print("ALL LIVE CHECKS COMPLETED!")
print("=" * 60)
