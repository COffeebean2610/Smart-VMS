import os
import datetime

p1 = r'dist\backend\backend.exe'
p2 = r'dist\electron\win-unpacked\resources\backend\backend.exe'
live_py = r'backend\app\api\live.py'

e1 = os.path.exists(p1)
e2 = os.path.exists(p2)

print(f"1. dist\\backend\\backend.exe exists: {e1}")
print(f"2. dist\\electron\\win-unpacked\\resources\\backend\\backend.exe exists: {e2}")

if e1 and e2:
    s1 = os.stat(p1)
    s2 = os.stat(p2)
    s_live = os.stat(live_py)

    t1 = datetime.datetime.fromtimestamp(s1.st_mtime)
    t2 = datetime.datetime.fromtimestamp(s2.st_mtime)
    t_live = datetime.datetime.fromtimestamp(s_live.st_mtime)

    print(f"   dist backend size: {s1.st_size} bytes, mtime: {t1}")
    print(f"   unpacked backend size: {s2.st_size} bytes, mtime: {t2}")
    print(f"   live.py mtime: {t_live}")
    print(f"3. Sizes match: {s1.st_size == s2.st_size}")
    print(f"   Timestamps match (within 2s): {abs(s1.st_mtime - s2.st_mtime) < 2}")
    print(f"4. Created AFTER Optional fix: {s1.st_mtime > s_live.st_mtime}")
