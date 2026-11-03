"""Constant-time comparison for ASCII HTTP credentials; malformed input denies."""
import secrets


def credential_matches(actual: str, expected: str) -> bool:
    # HTTP headers decode as Latin-1, but compare_digest(str, str) accepts ASCII only.
    return actual.isascii() and expected.isascii() and secrets.compare_digest(actual, expected)
