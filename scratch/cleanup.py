import os
import psutil

for proc in psutil.process_iter(['pid', 'name']):
    try:
        n = proc.info['name']
        if n and ('smartvms' in n.lower() or 'backend.exe' in n.lower()):
            proc.kill()
    except Exception:
        pass
