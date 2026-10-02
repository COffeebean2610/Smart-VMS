import py_compile
import sys

files = [
    r"backend\app\services\camera_service.py",
    r"backend\app\services\frame_processor.py",
    r"backend\app\api\cameras.py",
    r"backend\app\api\system.py",
    r"backend\app\api\notifications.py",
    r"backend\main.py",
]

for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"SYNTAX CHECK OK: {f}")
    except Exception as e:
        print(f"SYNTAX CHECK FAIL: {f}\n{e}")
        sys.exit(1)

print("ALL SYNTAX CHECKS PASSED!")

