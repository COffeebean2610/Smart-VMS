import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

def check_and_run_pyinstaller():
    print("==========================================")
    print("CHECKING PYINSTALLER API RUNNER")
    print("==========================================")
    try:
        import PyInstaller.__main__
        print(f"[SUCCESS] PyInstaller module loaded successfully!")
        
        spec_path = backend_dir / "backend.spec"
        print(f"Spec path: {spec_path}")
        
        # Execute PyInstaller build programmatically
        print("Starting PyInstaller build via Python API...")
        PyInstaller.__main__.run([
            str(spec_path),
            "--noconfirm",
            "--distpath", str(backend_dir / "dist"),
            "--workpath", str(backend_dir / "build"),
        ])
        print("[SUCCESS] PyInstaller build finished via Python API!")
        
    except ImportError:
        print("[ERROR] PyInstaller module is not installed in this Python environment.")
    except Exception as e:
        print(f"[ERROR] Exception during PyInstaller build: {e}")

if __name__ == "__main__":
    check_and_run_pyinstaller()
