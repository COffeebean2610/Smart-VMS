import os
import sys
import time
import datetime
import subprocess

p1 = os.path.join("dist", "backend", "backend.exe")
p2 = os.path.join("dist", "electron", "win-unpacked", "resources", "backend", "backend.exe")
live_py = os.path.join("backend", "app", "api", "live.py")
app_exe = os.path.join("dist", "electron", "win-unpacked", "SmartVMS.exe")

e1 = os.path.exists(p1)
e2 = os.path.exists(p2)

print("==================================================")
print("BUILD VERIFICATION:")
print(f"1. dist/backend/backend.exe exists: {e1}")
print(f"2. unpacked backend.exe exists: {e2}")

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
    print(f"3. Both have same size: {s1.st_size == s2.st_size}")
    print(f"   Both have matching timestamps (within 5s): {abs(s1.st_mtime - s2.st_mtime) < 5}")
    print(f"4. Packaged backend created AFTER Optional fix: {s1.st_mtime > s_live.st_mtime}")

print("\n==================================================")
print("LAUNCHING SMARTVMS.EXE...")
if os.path.exists(app_exe):
    proc = subprocess.Popen([os.path.abspath(app_exe)], cwd=os.path.dirname(os.path.abspath(app_exe)))
    print(f"SmartVMS.exe launched with PID {proc.pid}")
else:
    print(f"ERROR: {app_exe} not found!")
print("==================================================")
