import os
import sys
import subprocess
import shutil
from pathlib import Path

def rebuild_all():
    root_dir = Path(__file__).resolve().parent
    backend_dir = root_dir / "backend"
    frontend_dir = root_dir / "frontend"
    spec_file = backend_dir / "backend.spec"

    print("==================================================")
    print("REBUILDING BACKEND AND FRONTEND FOR ELECTRON FIXES")
    print("==================================================")

    # 1. Rebuild PyInstaller backend
    print("\n1. Rebuilding PyInstaller backend...")
    py_executable = backend_dir / "venv" / "Scripts" / "python.exe"
    if not py_executable.exists():
        py_executable = sys.executable

    cmd = [str(py_executable), "-m", "PyInstaller", str(spec_file), "--noconfirm"]
    res = subprocess.run(cmd, cwd=str(backend_dir))
    if res.returncode != 0:
        print(f"Backend build failed with exit code {res.returncode}")
        sys.exit(1)
    print("PyInstaller backend build SUCCESS!")

    # 2. Rebuild React frontend
    print("\n2. Rebuilding React production frontend...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    res = subprocess.run([npm_cmd, "run", "build"], cwd=str(frontend_dir))
    if res.returncode != 0:
        print(f"Frontend build failed with exit code {res.returncode}")
        sys.exit(1)
    print("React production build SUCCESS!")

    print("\n==================================================")
    print("ALL FIXES REBUILT CLEANLY. READY FOR ELECTRON DIST")
    print("==================================================")

if __name__ == "__main__":
    rebuild_all()
