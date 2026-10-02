import os
import sys
import subprocess
from pathlib import Path

def build():
    backend_dir = Path(__file__).resolve().parent
    spec_file = backend_dir / "backend.spec"

    print("==========================================")
    print("SMART VMS — PYINSTALLER BACKEND BUILD")
    print("==========================================")
    print(f"Working Directory: {backend_dir}")
    print(f"Spec File: {spec_file}")
    
    if not spec_file.exists():
        print(f"Error: Spec file not found at {spec_file}")
        sys.exit(1)

    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--noconfirm"]
    print("Executing command:", " ".join(cmd))
    print("------------------------------------------")

    try:
        res = subprocess.run(cmd, cwd=str(backend_dir))
        if res.returncode == 0:
            dist_dir = backend_dir / "dist" / "backend"
            exe_path = dist_dir / "backend.exe"
            print("==========================================")
            print("BUILD SUCCESSFUL!")
            print(f"Output Directory: {dist_dir}")
            print(f"Backend Executable: {exe_path}")
            print("==========================================")
        else:
            print(f"Build failed with return code {res.returncode}")
            sys.exit(res.returncode)
    except Exception as e:
        print("Build execution exception:", e)
        sys.exit(1)

if __name__ == "__main__":
    build()
