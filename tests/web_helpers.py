import re


def csrf_token(html: str) -> str:
    match = re.search(r'name=["\']csrf_token["\'][^>]+value=["\']([^"\']+)["\']', html)
    assert match is not None, "csrf token is missing from form"
    return match.group(1)
