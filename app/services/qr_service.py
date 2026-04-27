"""
QR Service — ZamID Connect (v2, International-Grade Security)

Architecture follows:
  - ISO/IEC 18013-5 (mobile ID concepts)
  - NIST 800-63 (identity assurance)
  - JWT with jti + exp (one-time, time-limited tokens)
  - Data minimization: QR never contains full NRC or sensitive fields

Flow:
  1. generate_qr_token()  → creates a signed JWT (60-second expiry, unique jti)
  2. verify_qr_token()    → validates signature, expiry, and one-time-use (jti blacklist)
  3. get_safe_citizen()   → strips sensitive fields (data minimisation — GDPR style)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Set

from jose import JWTError, jwt

from app.config.settings import settings

# ---------------------------------------------------------------------------
# In-process token blacklist (used JTI store)
# In production: replace with Redis  →  redis_client.setex(jti, 120, "used")
# ---------------------------------------------------------------------------
_used_jtis: Set[str] = set()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
QR_TOKEN_ALGORITHM = "HS256"
QR_TOKEN_EXPIRE_SECONDS = 60   # 60-second window — enough for a scanner
QR_TOKEN_VERSION = "2.0"

# ---------------------------------------------------------------------------
# Fields exposed when a QR is scanned  (data minimisation)
# Never expose: nrc_number, address, phone, documents, raw id
# ---------------------------------------------------------------------------
SAFE_CITIZEN_FIELDS = {"id", "first_name", "last_name", "status", "province"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_qr_token(citizen: dict) -> str:
    """
    Issue a signed JWT QR token.

    Payload:
        sub   — citizen UUID
        jti   — unique token ID (prevents replay)
        exp   — 60-second expiry (UNIX timestamp)
        iat   — issued-at
        ver   — schema version
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=QR_TOKEN_EXPIRE_SECONDS)

    payload = {
        "sub": str(citizen["id"]),
        "jti": str(uuid.uuid4()),       # unique token ID — used for one-time enforcement
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "ver": QR_TOKEN_VERSION,
    }

    token = jwt.encode(
        payload,
        settings.QR_SIGNING_SECRET,
        algorithm=QR_TOKEN_ALGORITHM,
    )
    return token


def verify_qr_token(token: str) -> Tuple[bool, Dict]:
    """
    Verify a QR token.  Returns (valid: bool, result: dict).

    Checks:
      1. Signature validity
      2. Token not expired (exp)
      3. jti not already used (one-time use)

    On success:  marks jti as used and returns the decoded payload.
    On failure:  returns a reason code without leaking internal details.
    """
    try:
        payload = jwt.decode(
            token,
            settings.QR_SIGNING_SECRET,
            algorithms=[QR_TOKEN_ALGORITHM],
        )
    except JWTError as exc:
        reason = "expired" if "expired" in str(exc).lower() else "invalid_token"
        return False, {"reason": reason}

    jti = payload.get("jti")
    if not jti:
        return False, {"reason": "missing_jti"}

    # One-time use check
    if jti in _used_jtis:
        return False, {"reason": "token_already_used"}

    # Mark as used immediately to prevent race-condition replays
    _used_jtis.add(jti)

    return True, payload


def get_safe_citizen(citizen: dict) -> dict:
    """
    Return only the fields that should be shown to a scanner (data minimisation).
    Full NRC, address, phone, documents are NEVER returned.
    """
    return {k: v for k, v in citizen.items() if k in SAFE_CITIZEN_FIELDS}


# ---------------------------------------------------------------------------
# Legacy HMAC helpers — kept for backward compatibility, deprecated in v2
# Remove once all clients have migrated to JWT QR tokens.
# ---------------------------------------------------------------------------
import hmac
import hashlib
import json

def generate_qr_payload(citizen: dict) -> str:
    """[DEPRECATED v1] HMAC-signed JSON payload. Use generate_qr_token() instead."""
    timestamp = datetime.utcnow().isoformat()
    message = f"{citizen['id']}:{citizen['nrc_number']}:{timestamp}"
    signature = hmac.new(
        settings.QR_SIGNING_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    payload = {
        "citizen_id": citizen["id"],
        "nrc_number": citizen["nrc_number"],
        "first_name": citizen["first_name"],
        "last_name":  citizen["last_name"],
        "status":     citizen["status"],
        "province":   citizen["province"],
        "timestamp":  timestamp,
        "signature":  signature,
        "version":    "1.0",
    }
    return json.dumps(payload)
