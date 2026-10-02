import os
import sys
import json
from pathlib import Path

def run_verification():
    root_dir = Path(__file__).resolve().parent
    dist_backend_exe = root_dir / "dist" / "backend" / "backend.exe"
    unpacked_backend_exe = root_dir / "dist" / "electron" / "win-unpacked" / "resources" / "backend" / "backend.exe"
    live_py = root_dir / "backend" / "app" / "api" / "live.py"
    smartvms_exe = root_dir / "dist" / "electron" / "win-unpacked" / "SmartVMS.exe"

    print("==================================================")
    print("FRESH PRODUCTION BUILD & LAUNCH VERIFICATION")
    print("==================================================")

    e1 = dist_backend_exe.exists()
    e2 = unpacked_backend_exe.exists()
    e_live = live_py.exists()

    print(f"1. dist\\backend\\backend.exe exists: {e1}")
    print(f"2. dist\\electron\\win-unpacked\\resources\\backend\\backend.exe exists: {e2}")

    if e1 and e2 and e_live:
        s1 = dist_backend_exe.stat()
        s2 = unpacked_backend_exe.stat()
        s_live = live_py.stat()

        t1 = datetime.datetime.fromtimestamp(s1.st_mtime)
        t2 = datetime.datetime.fromtimestamp(s2.st_mtime)
        t_live = datetime.datetime.fromtimestamp(s_live.st_mtime)

        print(f"   dist backend size: {s1.st_size} bytes | mtime: {t1}")
        print(f"   unpacked backend size: {s2.st_size} bytes | mtime: {t2}")
        print(f"   live.py mtime: {t_live}")

        print(f"3. Both have same size: {s1.st_size == s2.st_size}")
        print(f"   Both have matching timestamps (within 5s): {abs(s1.st_mtime - s2.st_mtime) < 5}")
        print(f"4. Packaged backend created AFTER Optional fix: {s1.st_mtime > s_live.st_mtime}")

    print("\n==================================================")
    print("VERIFICATION OF PACKAGED EXECUTABLES COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    import datetime
    run_verification()

