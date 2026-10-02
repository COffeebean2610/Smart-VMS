import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from app.api import live
    print("app.api.live imported SUCCESSFULLY with zero NameError/ImportError!")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)
