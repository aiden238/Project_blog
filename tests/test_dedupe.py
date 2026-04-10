from src.dedupe import SIMHASH_HAMMING_THRESHOLD, compute_simhash64, hamming_distance


def test_simhash_distance_is_small_for_near_duplicate_text() -> None:
    left = compute_simhash64(
        "OpenAI released a new reasoning model today. The update improves coding quality, "
        "tool use, and latency across benchmark tasks. The post includes evaluation charts "
        "and migration notes for developers."
    )
    right = compute_simhash64(
        "OpenAI released a new reasoning model today. The update improves coding quality, "
        "tool usage, and latency across benchmark tasks. The post includes evaluation charts "
        "and migration notes for developers."
    )

    assert hamming_distance(left, right) <= SIMHASH_HAMMING_THRESHOLD
