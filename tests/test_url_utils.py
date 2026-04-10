from src.url_utils import normalize_url


def test_normalize_url_removes_tracking_params_and_sorts_query() -> None:
    url = "https://Example.com/path?b=2&utm_source=x&a=1&gclid=abc#section"

    normalized = normalize_url(url)

    assert normalized == "https://example.com/path?a=1&b=2"
