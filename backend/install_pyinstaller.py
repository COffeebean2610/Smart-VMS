import sys

def check_or_install():
    print("==========================================")
    print("PYINSTALLER ENVIRONMENT DIAGNOSTIC & INSTALL")
    print("==========================================")
    print(f"Active Python Interpreter: {sys.executable}")
    print(f"Python Version: {sys.version}")

    try:
        import PyInstaller
        print(f"[STATUS] PyInstaller is ALREADY installed! Version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("[STATUS] PyInstaller is NOT installed in active environment.")
        print("Installing pyinstaller via internal pip module API...")
        try:
            from pip._internal.cli.main import main as pip_main
            exit_code = pip_main(["install", "pyinstaller"])
            print(f"[STATUS] Pip install returned code: {exit_code}")
            
            import PyInstaller
            print(f"[SUCCESS] PyInstaller successfully installed! Version: {PyInstaller.__version__}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to install PyInstaller: {e}")
            return False

if __name__ == "__main__":
    check_or_install()
