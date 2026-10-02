import sys

print("Checking PyInstaller module availability...")
try:
    import PyInstaller
    print(f"PyInstaller Version: {PyInstaller.__version__}")
except ImportError:
    print("PyInstaller is not installed in the current Python environment.")
