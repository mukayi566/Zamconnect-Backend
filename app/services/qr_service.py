import hmac
import hashlib
import json
from datetime import datetime
from typing import Dict, Tuple
from app.config.settings import settings

def generate_qr_payload(citizen: dict) -> str:
    timestamp = datetime.utcnow().isoformat()
    # Unique message for signing
    message = f"{citizen['id']}:{citizen['nrc_number']}:{timestamp}"
    
    signature = hmac.new(
        settings.QR_SIGNING_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    payload = {
        "citizen_id":  citizen["id"],
        "nrc_number":  citizen["nrc_number"],
        "first_name":  citizen["first_name"],
        "last_name":   citizen["last_name"],
        "status":      citizen["status"],
        "province":    citizen["province"],
        "timestamp":   timestamp,
        "signature":   signature,
        "version":     "1.0"
    }
    return json.dumps(payload)

def verify_qr_payload(payload_str: str) -> Tuple[bool, Dict]:
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        return False, {"reason": "invalid_format"}

    required_fields = ["citizen_id", "nrc_number", "timestamp", "signature"]
    if not all(field in payload for field in required_fields):
        return False, {"reason": "missing_fields"}

    message = f"{payload['citizen_id']}:{payload['nrc_number']}:{payload['timestamp']}"
    expected = hmac.new(
        settings.QR_SIGNING_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    # Timing-safe comparison
    if not hmac.compare_digest(expected, payload.get("signature", "")):
        return False, {"reason": "tampered"}

    # Optional: Check if expired (e.g. 1 year)
    # ... logic here ...

    return True, payload
