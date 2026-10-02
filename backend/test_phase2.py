import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.core.security import encrypt_secret, decrypt_secret
from app.db.database import (
    db_manager,
    connect_to_mongo,
    close_mongo_connection,
    get_db_status_info,
    DBStatus,
)

async def run_phase2_tests():
    print("==========================================")
    print("RUNNING PHASE 2 MONGODB RESILIENCE TESTS")
    print("==========================================")

    # Test 1: DPAPI Secret Encryption / Decryption
    secret = "mongodb+srv://myuser:mypassword123@cluster0.mongodb.net/smart_vms"
    encrypted = encrypt_secret(secret)
    decrypted = decrypt_secret(encrypted)
    print(f"[TEST 1] Encrypted format: {encrypted[:25]}...")
    print(f"[TEST 1] Decrypted match: {decrypted == secret}")
    assert decrypted == secret, "DPAPI Encryption/Decryption roundtrip failed!"

    # Test 2: URI Sanitization / Redaction
    sanitized = db_manager.sanitize_uri_for_logging(secret)
    print(f"[TEST 2] Sanitized URI: {sanitized}")
    assert "myuser" not in sanitized and "mypassword123" not in sanitized, "URI sanitization exposed credentials!"
    assert "***:***" in sanitized, "URI sanitization format failed!"

    # Test 3: Invalid URI Resilient Failure (No Backend Crash)
    invalid_uri = "mongodb+srv://baduser:badpass@invalidcluster999999.mongodb.net/smart_vms"
    print(f"[TEST 3] Testing connection to invalid URI (should fail gracefully in <=5s)...")
    success_invalid = await connect_to_mongo(uri_override=invalid_uri)
    status_invalid = get_db_status_info()
    print(f"[TEST 3] Connect Result: {success_invalid} (Expected: False)")
    print(f"[TEST 3] Status: {status_invalid['status']} (Expected: disconnected)")
    print(f"[TEST 3] Error message set: {bool(status_invalid['lastError'])}")
    assert not success_invalid, "Invalid URI connection unexpectedly succeeded!"
    assert status_invalid['status'] == DBStatus.DISCONNECTED.value, "Status was not set to disconnected!"

    # Test 4: Real MongoDB Connection Recovery
    print(f"[TEST 4] Testing connection recovery with real configured URI...")
    success_real = await connect_to_mongo()
    status_real = get_db_status_info()
    print(f"[TEST 4] Connect Result: {success_real}")
    print(f"[TEST 4] Status: {status_real['status']}")
    print(f"[TEST 4] Message: {status_real['message']}")
    assert success_real, "Real MongoDB Atlas connection failed!"
    assert status_real['status'] == DBStatus.CONNECTED.value, "Status was not set to connected!"

    # Clean up
    await close_mongo_connection()

    print("==========================================")
    print("ALL PHASE 2 MONGODB RESILIENCE TESTS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(run_phase2_tests())
