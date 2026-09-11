"""
KAIRO Network & Client Resolution Utilities.
Ensures secure client IP extraction for rate limiting and audit logging
without allowing untrusted clients to spoof their IP via X-Forwarded-For.
"""

from fastapi import Request


def get_client_ip(request: Request, trusted_proxies: list[str] | None = None) -> str:
    """
    Extracts the true client IP address safely.
    
    Security Rules:
    1. If request.client is None, return 'unknown'.
    2. If request.client.host is NOT in trusted_proxies, DO NOT trust X-Forwarded-For.
       Return request.client.host directly to prevent spoofing.
    3. If request.client.host IS in trusted_proxies:
       Parse X-Forwarded-For (comma-separated client IPs from left to right).
       Walk right-to-left stripping trusted proxies to identify the first untrusted IP.
       If all are trusted or format is invalid, return the leftmost valid IP.
    """
    if not request.client or not request.client.host:
        return "unknown"

    direct_ip = request.client.host.strip()
    trusted = set(trusted_proxies or ["127.0.0.1", "::1"])

    # If the connecting client is not a trusted reverse proxy, use direct IP
    if direct_ip not in trusted:
        return direct_ip

    # Connecting client is a trusted proxy, inspect X-Forwarded-For
    xff = request.headers.get("x-forwarded-for")
    if not xff:
        return direct_ip

    hops = [ip.strip() for ip in xff.split(",") if ip.strip()]
    if not hops:
        return direct_ip

    # Walk from right to left, stripping any intermediate trusted proxies
    for hop in reversed(hops):
        if hop not in trusted:
            return hop

    # If all hops are in trusted set, return the original client (leftmost)
    return hops[0]
