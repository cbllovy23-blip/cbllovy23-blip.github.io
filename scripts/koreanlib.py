"""Shared helpers for classifying Korean vs English text.
Mirrors the koreanRatio/isCurrentStyle logic used in the CBL walk
title/description rewrite project (YouTube Data API browser scripts),
so results stay consistent with how the channel's own titles were judged.
"""
import re

HANGUL_RE = re.compile(r'[가-힣]')
LETTER_RE = re.compile(r'[^\s\d\W]', re.UNICODE)


def korean_ratio(s: str) -> float:
    """Fraction of letter characters in s that are Hangul."""
    letters = LETTER_RE.findall(s)
    if not letters:
        return 0.0
    hangul = HANGUL_RE.findall(s)
    return len(hangul) / len(letters)


def is_english_line(line: str, threshold: float = 0.2) -> bool:
    """A line counts as 'English' if its Korean-character ratio is below
    threshold. Lines with no letters at all (pure URL, pure emoji, blank)
    are treated as English/neutral so they are kept rather than dropped."""
    stripped = line.strip()
    if not stripped:
        return False
    return korean_ratio(stripped) < threshold


CREDIT_MARKERS = [
    'bensound', 'music by', 'license', 'licence', 'youtube audio library',
    'track:', 'song:', 'artist:', 'soundcloud', 'creative commons',
    'courtesy of epidemic', 'epidemic sound',
]


def is_credit_line(line: str) -> bool:
    low = line.lower()
    return any(marker in low for marker in CREDIT_MARKERS)
