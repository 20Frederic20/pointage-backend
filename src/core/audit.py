"""Audit logger — console only, no DB.

Usage in any handler:
    from core.audit import audit
    audit.info("action=LOGIN_PASSWORD identifier=%s user_id=%s status=OK", ...)

Configure the root or 'audit' logger level in your FastAPI startup if needed.
By default Python logs WARNING+, so add this once in main.py / lifespan:

    import logging
    logging.getLogger("audit").setLevel(logging.INFO)
"""

import logging

audit = logging.getLogger("audit")