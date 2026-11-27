"""Strict URL validation for the Android companion's visible browser handoff.

Only ordinary HTTPS navigation is supported. No intent:, file:, content:, data:,
javascript:, credential-bearing, cleartext, non-default-port or control-bearing
URL is eligible. The full URL is intentionally kept out of the Termux audit DB
and Store packets; only its digest and public host are retained there.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

MAX_HTTPS_URL_LENGTH = 2048
_BAD_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")


class UnsafeAndroidUrl(ValueError):
    pass


def validate_https_url(value: object) -> str:
    if (type(value) is not str or not 9 <= len(value) <= MAX_HTTPS_URL_LENGTH
            or not value.startswith("https://") or not value.isascii()
            or "\\" in value or _BAD_PERCENT.search(value)):
        raise UnsafeAndroidUrl("only a bounded ASCII HTTPS URL is allowed")
    if any(ord(char) <= 0x20 or ord(char) >= 0x7f for char in value):
        raise UnsafeAndroidUrl("URL contains whitespace or control characters")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as exc:
        raise UnsafeAndroidUrl("URL authority is malformed") from exc
    authority = parts.netloc
    host = parts.hostname
    if (parts.scheme != "https" or not authority or not host
            or parts.username is not None or parts.password is not None
            or port not in (None, 443) or authority.endswith(":")
            or "%" in authority or len(host) > 253):
        raise UnsafeAndroidUrl("URL must use HTTPS without credentials or a non-default port")
    return value


def https_host(value: object) -> str:
    return urlsplit(validate_https_url(value)).hostname.lower()
