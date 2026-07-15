#!/usr/bin/env python3
"""Check available credits on flowmusic.app via authed API."""
import sys
sys.path.insert(0, "/home/rafael/.openclaw/workspace/tools")
from producer_common import ProducerSession

s = ProducerSession()
try:
    jwt = s.jwt()
    print("JWT_OK" if jwt else "JWT_MISSING", flush=True)
    r = s.api_get("/__api/billing/credits")
    print("STATUS", r.status, flush=True)
    body = r.text()
    print("BODY", body[:500], flush=True)
finally:
    s.close()
