from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"fbclid", "gclid"}


def is_tracking_parameter(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith("utm_") or lowered in TRACKING_PARAMS


def normalize_url(url: str) -> str:
    split = urlsplit(url.strip())
    query_items = parse_qsl(split.query, keep_blank_values=True)
    filtered_items = [
        (key, value) for key, value in query_items if not is_tracking_parameter(key)
    ]
    filtered_items.sort(key=lambda item: (item[0], item[1]))

    path = split.path or "/"
    query = urlencode(filtered_items, doseq=True)

    normalized = urlunsplit(
        (
            split.scheme.lower(),
            split.netloc.lower(),
            path,
            query,
            "",
        )
    )
    return normalized
