import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_fresh_package():
    root_dir = Path(__file__).resolve().parent
    backend_dir = root_dir / "backend"
    frontend_dir = root_dir / "frontend"
    spec_file = backend_dir / "backend.spec"
    dist_electron = root_dir / "dist" / "electron"

    print("==================================================")
    print("PHASE 5 — BUILDING FRESH PACKAGED BACKEND & ELECTRON DISTRIBUTION")
    print("==================================================")

    # Clean running processes locking dist files
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            n = proc.info.get('name')
            if n and ('smartvms' in n.lower() or 'backend.exe' in n.lower()):
                try:
                    proc.kill()
                except Exception:
                    pass
    except Exception:
        pass

    # Clean old PyInstaller build outputs before building
    root_dist_backend = root_dir / "dist" / "backend"
    backend_dist = backend_dir / "dist"
    if root_dist_backend.exists():
        print("Cleaning old root dist/backend...")
        shutil.rmtree(root_dist_backend, ignore_errors=True)
    if backend_dist.exists():
        print("Cleaning old backend/dist...")
        shutil.rmtree(backend_dist, ignore_errors=True)

    # 0. Generate Application Icons
    print("\n0. Generating Application Icons...")
    py_executable = backend_dir / "venv" / "Scripts" / "python.exe"
    if not py_executable.exists():
        py_executable = sys.executable

    icon_script = root_dir / "generate_app_icon.py"
    if icon_script.exists():
        subprocess.run([str(py_executable), str(icon_script)], cwd=str(root_dir))

    # 1. Rebuild PyInstaller backend executable explicitly into project root dist/
    print("\n1. Rebuilding PyInstaller backend executable...")


    cmd = [
        str(py_executable),
        "-m",
        "PyInstaller",
        str(spec_file),
        "--distpath",
        str(root_dir / "dist"),
        "--noconfirm",
    ]
    print("Executing command:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(backend_dir))
    if res.returncode != 0:
        print(f"PyInstaller build failed with exit code {res.returncode}")
        sys.exit(1)
    print("PyInstaller backend build SUCCESS!")

    # Verify PyInstaller build outputs
    exe_path = root_dir / "dist" / "backend" / "backend.exe"
    c_stable_path = list(root_dir.glob("dist/backend/**/_C_stable.pyd"))
    if not exe_path.exists():
        print(f"ERROR: {exe_path} does not exist!")
        sys.exit(1)
    print(f" - Verified backend.exe: {exe_path}")
    print(f" - Verified _C_stable.pyd: {c_stable_path[0] if c_stable_path else 'NOT FOUND'}")

    # 2. Rebuild React production frontend
    print("\n2. Rebuilding React production frontend...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    res = subprocess.run([npm_cmd, "run", "build"], cwd=str(frontend_dir))
    if res.returncode != 0:
        print(f"Frontend build failed with exit code {res.returncode}")
        sys.exit(1)
    print("React production build SUCCESS!")

    # 3. Clean dist/electron
    if dist_electron.exists():
        print("\nCleaning dist/electron...")
        shutil.rmtree(dist_electron, ignore_errors=True)

    # 4. Rebuild Electron package with electron-builder
    print("\n3. Rebuilding Electron package...")
    res = subprocess.run([npm_cmd, "run", "dist"], cwd=str(root_dir))
    if res.returncode != 0:
        print(f"Electron build failed with exit code {res.returncode}")
        sys.exit(1)
    print("Electron packaging SUCCESS!")

    # 5. Verify final packaged outputs
    unpacked_exe = dist_electron / "win-unpacked" / "SmartVMS.exe"
    unpacked_backend = dist_electron / "win-unpacked" / "resources" / "backend" / "backend.exe"
    unpacked_c_stable = list(dist_electron.rglob("_C_stable.pyd"))

    print("\n==================================================")
    print("FINAL PACKAGED VERIFICATION SUMMARY:")
    print(f" - SmartVMS.exe: {unpacked_exe} ({'PASS' if unpacked_exe.exists() else 'FAIL'})")
    print(f" - Bundled backend.exe: {unpacked_backend} ({'PASS' if unpacked_backend.exists() else 'FAIL'})")
    print(f" - Bundled _C_stable.pyd: {unpacked_c_stable[0] if unpacked_c_stable else 'FAIL'}")
    print("==================================================")

if __name__ == "__main__":
    build_fresh_package()
