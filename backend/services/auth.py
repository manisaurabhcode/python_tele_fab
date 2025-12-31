
# app/backend/services/auth.py
import os, json, hmac, hashlib, base64, time
from typing import Dict, Any, Optional

SECRET = os.getenv("APP_SECRET", "dev-secret-change-me")  # change in prod
TOKEN_TTL_SEC = int(os.getenv("TOKEN_TTL_SEC", "3600"))   # 1 hour

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def sign_token(payload: Dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    return f"{_b64url_encode(body)}.{_b64url_encode(sig)}"

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        body_b64, sig_b64 = token.split(".")
        body = _b64url_decode(body_b64)
        exp_sig = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).digest()
        if not hmac.compare_digest(exp_sig, _b64url_decode(sig_b64)):
            return None
        payload = json.loads(body.decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

def issue_token(username: str) -> str:
    now = int(time.time())
    payload = {"user": username, "iat": now, "exp": now + TOKEN_TTL_SEC}
    return sign_token(payload)
