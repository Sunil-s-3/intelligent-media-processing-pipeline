"""Perceptual-hash duplicate detection.

Uses imagehash pHash (64-bit). Comparison is Hamming distance on the hashes,
never filenames.

Efficiency
----------
This take-home scans stored hashes for the current dataset. That is acceptable
for thousands of images. Production would need an approximate nearest-neighbor
index (e.g. FAISS, pgvector bit distance, or a dedicated pHash store).
"""

from __future__ import annotations

from pathlib import Path

import imagehash
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.analyzers.common import clamp_confidence
from app.core.config import settings
from app.db.models import Image


def compute_phash(image_path: Path) -> str:
    with PILImage.open(image_path) as img:
        return str(imagehash.phash(img))


def hamming_distance(hash_a: str, hash_b: str) -> int:
    return int(imagehash.hex_to_hash(hash_a) - imagehash.hex_to_hash(hash_b))


def analyze_duplicate(
    image_path: Path,
    *,
    image_id: str,
    db: Session,
    max_distance: int | None = None,
) -> dict:
    max_distance = (
        settings.DUPLICATE_HASH_DISTANCE if max_distance is None else max_distance
    )
    current_hash = compute_phash(image_path)

    others = (
        db.query(Image.id, Image.perceptual_hash)
        .filter(Image.id != image_id, Image.perceptual_hash.isnot(None))
        .all()
    )

    if not others:
        return {
            "detected": False,
            "matched_image_id": None,
            "similarity": None,
            "hamming_distance": None,
            "perceptual_hash": current_hash,
            "confidence": 0.6,
            "reason": "No previously processed images with a perceptual hash to compare",
            "method": "phash_hamming",
            "confidence_note": (
                "Heuristic score; pHash can miss crops/rotations and can collide"
            ),
        }

    best_id: str | None = None
    best_distance = 65
    for other_id, other_hash in others:
        if not other_hash:
            continue
        distance = hamming_distance(current_hash, other_hash)
        if distance < best_distance:
            best_distance = distance
            best_id = other_id

    similarity = round(1.0 - (best_distance / 64.0), 4)
    detected = best_id is not None and best_distance <= max_distance

    if detected:
        if best_distance == 0:
            raw = 0.97
            reason = "Exact perceptual-hash match with a previously stored image"
        else:
            raw = 0.6 + 0.35 * (1.0 - (best_distance / max(max_distance, 1)))
            reason = (
                f"Near-duplicate: Hamming distance {best_distance} is within "
                f"threshold {max_distance}"
            )
        matched = best_id
    else:
        raw = 0.55 + 0.4 * min(1.0, (best_distance - max_distance) / 32.0)
        reason = (
            f"Closest prior image has Hamming distance {best_distance}, "
            f"above threshold {max_distance}"
        )
        matched = None

    return {
        "detected": detected,
        "matched_image_id": matched,
        "similarity": similarity,
        "hamming_distance": best_distance,
        "perceptual_hash": current_hash,
        "threshold": max_distance,
        "confidence": clamp_confidence(raw),
        "reason": reason,
        "method": "phash_hamming",
        "confidence_note": (
            "Heuristic score; pHash can miss crops/rotations and can collide"
        ),
    }
