import os
import sys
import base64
import logging
import ctypes
from ctypes import wintypes

logger = logging.getLogger(__name__)


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def encrypt_secret(plaintext: str) -> str:
    """
    Encrypts a sensitive string (e.g. MONGO_URI) for local Windows desktop storage.
    Uses Windows DPAPI (CryptProtectData via ctypes) on Windows.
    Falls back to base64 encoding on non-Windows environments.
    """
    if not plaintext:
        return ""

    if sys.platform.startswith("win"):
        try:
            data = plaintext.encode("utf-8")
            blob_in = DATA_BLOB(len(data), (ctypes.c_byte * len(data))(*data))
            blob_out = DATA_BLOB()

            if ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(blob_in),
                "SmartVMS Secret",
                None,
                None,
                None,
                0,
                ctypes.byref(blob_out),
            ):
                encrypted_bytes = bytes(
                    (ctypes.c_byte * blob_out.cbData).from_address(
                        ctypes.addressof(blob_out.pbData.contents)
                    )
                )
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                encoded = base64.b64encode(encrypted_bytes).decode("utf-8")
                return f"DPAPI:{encoded}"
        except Exception as e:
            logger.warning(f"[SECURITY] Windows DPAPI encryption error: {e}. Falling back to standard encoding.")

    encoded = base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")
    return f"ENC:{encoded}"


def decrypt_secret(ciphertext: str) -> str:
    """
    Decrypts a DPAPI or encoded sensitive string.
    """
    if not ciphertext:
        return ""

    if ciphertext.startswith("DPAPI:") and sys.platform.startswith("win"):
        try:
            raw_b64 = ciphertext[6:]
            encrypted_bytes = base64.b64decode(raw_b64)
            blob_in = DATA_BLOB(
                len(encrypted_bytes),
                (ctypes.c_byte * len(encrypted_bytes))(*encrypted_bytes),
            )
            blob_out = DATA_BLOB()

            if ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blob_in),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(blob_out),
            ):
                decrypted_bytes = bytes(
                    (ctypes.c_byte * blob_out.cbData).from_address(
                        ctypes.addressof(blob_out.pbData.contents)
                    )
                )
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                return decrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"[SECURITY] Windows DPAPI decryption failed: {e}")
            return ""

    if ciphertext.startswith("ENC:"):
        try:
            return base64.b64decode(ciphertext[4:]).decode("utf-8")
        except Exception as e:
            logger.error(f"[SECURITY] Base64 secret decryption failed: {e}")
            return ""

    # Return plaintext if un-prefixed (legacy/dev support)
    return ciphertext
