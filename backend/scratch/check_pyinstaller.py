import sys
import subprocess

print(f"Python executable: {sys.executable}")
try:
    import PyInstaller
    print(f"PyInstaller is installed! Version: {PyInstaller.__version__}")
except ImportError:
    print("PyInstaller is not installed. Attempting installation via python script...")
    try:
        res = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], capture_output=True, text=True)
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        print("Return code:", res.returncode)
    except Exception as e:
        print("Exception during pip install:", e)
