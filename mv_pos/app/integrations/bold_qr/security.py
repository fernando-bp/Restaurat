from __future__ import annotations

import hmac
from hashlib import sha256


def verify_bold_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret:
        return False

    expected = hmac.new(secret.encode("utf-8"), raw_body, sha256).hexdigest()
    normalized = signature.removeprefix("sha256=").strip()
    return hmac.compare_digest(expected, normalized)
