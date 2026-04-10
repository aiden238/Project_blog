from __future__ import annotations

import hashlib
import re

SIMHASH_HAMMING_THRESHOLD = 3
TOKEN_PATTERN = re.compile(r"[0-9A-Za-z_]+", re.UNICODE)


def tokenize_for_simhash(text: str) -> list[str]:
    normalized = " ".join(token.lower() for token in TOKEN_PATTERN.findall(text))
    if not normalized:
        return []
    if len(normalized) < 4:
        return [normalized]
    return [normalized[index : index + 4] for index in range(len(normalized) - 3)]


def compute_simhash64(text: str) -> str:
    tokens = tokenize_for_simhash(text)
    if not tokens:
        return "0" * 16

    vector = [0] * 64
    for token in tokens:
        token_hash = int.from_bytes(
            hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(),
            byteorder="big",
        )
        for offset in range(64):
            mask = 1 << offset
            vector[offset] += 1 if token_hash & mask else -1

    value = 0
    for offset, weight in enumerate(vector):
        if weight >= 0:
            value |= 1 << offset

    return f"{value:016x}"


def hamming_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()
