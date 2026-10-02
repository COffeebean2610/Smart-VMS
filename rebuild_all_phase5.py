import os
import sys
import subprocess
import shutil
from pathlib import Path

def rebuild_all():
    root_dir = Path(__file__).resolve().parent
    frontend_dir = root_dir / "frontend"
    backend_dir = root_dir / "backend"
    spec_file = backend_dir / "backend.spec"
    dist_electron = root_dir / "dist" / "electron"

    print("==================================================")
    print("PHASE 5 — COMPLETE REBUILD FOR MULTI-CAMERA/WEBSOCKET FIXES")
    print("==================================================")

    # 1. Clean old frontend build
    frontend_dist = frontend_dir / "dist"
    if frontend_dist.exists():
        print("Cleaning old frontend/dist...")
        shutil.rmtree(frontend_dist, ignore_errors=True)

    # 2. Build React production bundle
    print("\n1. Building React production bundle...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    res = subprocess.run([npm_cmd, "run", "build"], cwd=str(frontend_dir))
    if res.returncode != 0:
        print(f"Frontend build failed with exit code {res.returncode}")
        sys.exit(1)
    print("React production build SUCCESS!")

    # 3. Clean dist/electron only (preserving PyInstaller dist/backend)
    if dist_electron.exists():
        print("\nCleaning dist/electron...")
        shutil.rmtree(dist_electron, ignore_errors=True)

    # 4. Rebuild Electron Package
    print("\n2. Rebuilding Electron package...")
    res = subprocess.run([npm_cmd, "run", "dist"], cwd=str(root_dir))
    if res.returncode != 0:
        print(f"Electron build failed with exit code {res.returncode}")
        sys.exit(1)
    print("Electron packaging SUCCESS!")

    print("\n==================================================")
    print("PHASE 5 COMPLETE REBUILD PASSED 100%")
    print("==================================================")

if __name__ == "__main__":
    rebuild_all()
