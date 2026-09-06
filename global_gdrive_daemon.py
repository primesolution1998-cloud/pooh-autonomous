import time
import subprocess
import os

LOCAL_DIR = r'/home/max/pooh_workspace'
REMOTE_DIR = 'gdrive:Pooh_Autonomous'

def sync_to_cloud():
    print('[AUTOSYNC DAEMON] Syncing strictly pooh_workspace...')
    try:
        subprocess.run([
            'rclone', 'sync', LOCAL_DIR, REMOTE_DIR,
            '--exclude', '.git/**',
            '--exclude', 'venv/**',
            '--exclude', '__pycache__/**',
            '--exclude', '*.log',
            '--exclude', 'tasks_queue.json'
        ], check=True)
        print('[AUTOSYNC DAEMON] Sync completed successfully.')
    except Exception as e:
        print(f'[AUTOSYNC DAEMON ERROR] Sync failed: {e}')

if __name__ == '__main__':
    print('[AUTOSYNC DAEMON] Active for workspace:', LOCAL_DIR)
    while True:
        sync_to_cloud()
        time.sleep(20)
