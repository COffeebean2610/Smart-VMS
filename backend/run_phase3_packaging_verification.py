import os
import sys
import shutil
import time
import subprocess
import urllib.request
import json
from pathlib import Path

def run_verification():
    backend_dir = Path(__file__).resolve().parent
    root_dir = backend_dir.parent
    spec_file = backend_dir / "backend.spec"
    dist_dir = backend_dir / "dist" / "backend"
    exe_path = dist_dir / "backend.exe"

    print("==================================================")
    print("PHASE 3 — FRESH PYINSTALLER BUILD & VERIFICATION")
    print("==================================================")

    # 1. Environment check
    print(f"Python Version: {sys.version}")
    try:
        import PyInstaller
        print(f"PyInstaller Version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller NOT INSTALLED in this environment!")
        sys.exit(1)

    # 2. Stop running backend.exe process if any
    print("\nStopping any running backend.exe process...")
    subprocess.run(["powershell", "-Command", "Get-Process backend -ErrorAction SilentlyContinue | Stop-Process -Force"], capture_output=True)
    time.sleep(1)

    # 3. Clean previous build
    build_dir = backend_dir / "build"
    dist_parent = backend_dir / "dist"

    print("\nCleaning previous build and dist directories...")
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)
    if dist_parent.exists():
        shutil.rmtree(dist_parent, ignore_errors=True)
    print("Clean completed.")

    # 4. Build current backend
    print("\nBuilding PyInstaller package from backend.spec...")
    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--noconfirm"]
    res = subprocess.run(cmd, cwd=str(backend_dir))
    if res.returncode != 0:
        print(f"BUILD FAILED with exit code {res.returncode}")
        sys.exit(1)

    # 5. Verify build output files
    print("\nVerifying build output files...")
    if not exe_path.exists():
        print(f"ERROR: {exe_path} does not exist!")
        sys.exit(1)
    print(f" - Executable exists: {exe_path}")

    # Check _C_stable.pyd
    c_stable_files = list(dist_parent.rglob("_C_stable.pyd"))
    if not c_stable_files:
        print("ERROR: _C_stable.pyd NOT FOUND in dist!")
        sys.exit(1)
    print(f" - Found TorchVision native extension: {c_stable_files[0]}")

    # Check YOLO model
    model_file = dist_dir / "models" / "yolov8n.pt"
    if not model_file.exists():
        # Search anywhere under dist
        model_files = list(dist_parent.rglob("yolov8n.pt"))
        if not model_files:
            print("ERROR: yolov8n.pt model file NOT FOUND in dist!")
            sys.exit(1)
        print(f" - Found YOLO model: {model_files[0]}")
    else:
        print(f" - Found YOLO model: {model_file}")

    # 6. Launch packaged backend.exe
    print("\nLaunching packaged backend.exe on http://127.0.0.1:8000...")
    proc = subprocess.Popen(
        [str(exe_path), "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Wait for server startup
    healthy = False
    for i in range(25):
        time.sleep(1)
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
            if req.status == 200:
                healthy = True
                print(f"\nServer responded HTTP 200 OK after {i+1} seconds!")
                break
        except Exception:
            pass

    if not healthy:
        print("ERROR: Packaged backend server failed to respond within 25 seconds.")
        proc.terminate()
        out, _ = proc.communicate(timeout=5)
        print("Backend Console Output:\n", out)
        sys.exit(1)

    # Verify /docs endpoint
    docs_healthy = False
    try:
        req = urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=2)
        if req.status == 200:
            docs_healthy = True
            print("Swagger OpenAPI /docs endpoint responded HTTP 200 OK!")
    except Exception as e:
        print(f"Warning checking /docs: {e}")

    # Graceful shutdown test
    print("\nShutting down packaged backend server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
        print("Packaged backend process exited gracefully!")
    except subprocess.TimeoutExpired:
        proc.kill()
        print("Process killed after shutdown timeout.")

    print("\n==================================================")
    print("PHASE 3 PACKAGED BACKEND VERIFICATION COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    run_verification()
