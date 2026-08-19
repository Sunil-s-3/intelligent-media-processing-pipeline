"""Indian vehicle registration format validator.

This module only checks whether OCR text *resembles* common Indian registration
patterns. A match is **not** proof that the plate is genuine, issued, or
correctly read.

Assumptions and limitations
---------------------------
- Standard private/commercial format: 2-letter state code, 1-2 digit RTO code,
  1-3 letter series, 4-digit number (e.g. KA01AB1234, DL1CAA1234).
- Bharat series: YYBH####XX (e.g. 22BH1234AA).
- Matching is boundary-aware: spaces/hyphens between plate groups are allowed,
  but the entire OCR document is never concatenated and searched as one string.
- Diplomatic, armed-forces, temporary, and some special series are not covered.
- OCR errors (O vs 0, I vs 1) are not auto-corrected; that would hide uncertainty.
- A regex cannot verify that a state code is real or that a plate exists.
"""

from __future__ import annotations

import re

STANDARD_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")
BHARAT_PATTERN = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")

# Plate groups are at most 4 (state, RTO, series, number). Extra width covers
# OCR splitting a group (e.g. "KA 01 A B 1234") without joining a whole sentence.
_MAX_TOKEN_WINDOW = 6
_TOKEN_RE = re.compile(r"[A-Z0-9]+")


def normalize_plate_text(text: str) -> str:
    """Uppercase and drop spaces/hyphens/punctuation, keeping A-Z and digits."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _tokens(text: str) -> list[str]:
    """Alphanumeric OCR tokens. Spaces, hyphens, and punctuation are boundaries."""
    return _TOKEN_RE.findall(text.upper())


def _classify(candidate: str) -> str | None:
    if BHARAT_PATTERN.fullmatch(candidate):
        return "bharat_series"
    if STANDARD_PATTERN.fullmatch(candidate):
        return "standard"
    return None


def find_plate_candidates(text: str) -> list[tuple[str, str]]:
    """Return (value, pattern) pairs that full-match a plate pattern.

    Consecutive tokens separated by spaces/hyphens may be joined, so
    ``KA 01 AB 1234`` is accepted. Substring search over the fully
    concatenated OCR dump is intentionally not used: it fabricates plates
    from unrelated date/text sequences such as ``Tuesday, 17 Feb 2026``.
    """
    tokens = _tokens(text)
    bharat: list[tuple[str, str]] = []
    standard: list[tuple[str, str]] = []
    seen: set[str] = set()

    for i in range(len(tokens)):
        for width in range(1, _MAX_TOKEN_WINDOW + 1):
            if i + width > len(tokens):
                break
            candidate = "".join(tokens[i : i + width])
            if candidate in seen:
                continue
            label = _classify(candidate)
            if label is None:
                continue
            seen.add(candidate)
            if label == "bharat_series":
                bharat.append((candidate, label))
            else:
                standard.append((candidate, label))

    return bharat + standard


def validate_indian_plate(ocr_text: str | None) -> dict:
    if not ocr_text or not ocr_text.strip():
        return {
            "ocr_text": ocr_text,
            "normalized_text": None,
            "format_valid": False,
            "matched_value": None,
            "matched_pattern": None,
            "confidence": 0.0,
            "reason": "No OCR text available to validate against registration patterns",
        }

    compact = normalize_plate_text(ocr_text)
    candidates = find_plate_candidates(ocr_text)

    if candidates:
        value, pattern = candidates[0]
        return {
            "ocr_text": ocr_text,
            "normalized_text": compact,
            "format_valid": True,
            "matched_value": value,
            "matched_pattern": pattern,
            "confidence": 0.8 if pattern == "standard" else 0.75,
            "reason": (
                f"Extracted OCR tokens contain a sequence matching the {pattern} "
                "Indian registration pattern. This is format validation only, "
                "not proof the plate is genuine."
            ),
            "confidence_note": (
                "Heuristic: a regex match is not a calibrated probability and "
                "does not verify issuance"
            ),
        }

    return {
        "ocr_text": ocr_text,
        "normalized_text": compact,
        "format_valid": False,
        "matched_value": None,
        "matched_pattern": None,
        "confidence": 0.7,
        "reason": (
            "OCR text does not contain a sequence matching standard or "
            "Bharat-series Indian registration patterns"
        ),
        "confidence_note": (
            "Heuristic: missing a regex match may be OCR error, an unsupported "
            "series, or a non-plate image"
        ),
    }
