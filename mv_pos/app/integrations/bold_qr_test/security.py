from __future__ import annotations

import base64
import hmac
from hashlib import sha256


def verify_bold_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if signature is None:
        return False

    body_text = raw_body.decode("utf-8")
    encoded = base64.b64encode(body_text.encode("utf-8"))
    expected = hmac.new(secret.encode("utf-8"), encoded, sha256).hexdigest()
    return hmac.compare_digest(expected.encode("utf-8"), signature.strip().encode("utf-8"))
