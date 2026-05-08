"""
Rate limiting middleware using SlowAPI.
Provides two key functions:
  - get_remote_address  : IP-based limiting (SlowAPI built-in, for public endpoints)
  - get_user_id_or_ip   : User-ID-based limiting for authenticated endpoints
    (falls back to IP when no Bearer token is present)
"""
from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = logging.getLogger(__name__)


def get_user_id_or_ip(request: Request) -> str:
    """
    Rate-limit key for authenticated routes.
    Extracts the Clerk user-id from the JWT sub claim so that:
    - Users behind shared NAT aren't lumped together
    - Rotating IPs don't bypass per-user rate limits
    Falls back to IP address if no valid token is present.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass  # Fall through to IP
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_id_or_ip)
