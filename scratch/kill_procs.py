import os
import psutil

print("Checking and terminating processes using psutil...")
for proc in psutil.process_iter(['pid', 'name']):
    try:
        name = proc.info['name']
        if name and name.lower() in ['smartvms.exe', 'backend.exe']:
            print(f"Terminating process {name} (PID {proc.info['pid']})...")
            proc.terminate()
            proc.wait(timeout=3)
    except Exception as e:
        print(f"Error terminating process: {e}")

print("Clean process check finished.")
