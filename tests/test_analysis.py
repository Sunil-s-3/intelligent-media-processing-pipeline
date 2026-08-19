from app.analyzers.blur import analyze_blur
from app.analyzers.brightness import analyze_brightness
from app.analyzers.duplicate import analyze_duplicate, compute_phash, hamming_distance
from app.analyzers.plate_validator import validate_indian_plate
from app.db.models import Image, ProcessingStatus
from tests.helpers import blurred_image, bright_image, dark_image, noisy_image, save_png


def test_blur_detects_heavily_blurred_image(tmp_path):
    path = save_png(tmp_path / "blurry.png", blurred_image(radius=12))
    result = analyze_blur(path, threshold=100.0)
    assert result["detected"] is True
    assert result["score"] < 100.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert "blur" in result["reason"].lower() or "threshold" in result["reason"].lower()


def test_blur_does_not_flag_noisy_sharp_image(tmp_path):
    path = save_png(tmp_path / "sharp.png", noisy_image())
    result = analyze_blur(path, threshold=100.0)
    assert result["detected"] is False
    assert result["score"] >= 100.0


def test_brightness_detects_dark_image(tmp_path):
    path = save_png(tmp_path / "dark.png", dark_image())
    result = analyze_brightness(path, threshold=50.0)
    assert result["issue"] is True
    assert result["average_brightness"] < 50.0
    assert 0.0 <= result["confidence"] <= 1.0


def test_brightness_accepts_bright_image(tmp_path):
    path = save_png(tmp_path / "bright.png", bright_image())
    result = analyze_brightness(path, threshold=50.0)
    assert result["issue"] is False
    assert result["average_brightness"] >= 50.0


def test_duplicate_detects_same_image(tmp_path, db_session):
    first_path = save_png(tmp_path / "a.png", noisy_image(seed=3))
    second_path = save_png(tmp_path / "b.png", noisy_image(seed=3))

    first = Image(
        id="img-1",
        original_filename="a.png",
        stored_filename="a.png",
        storage_path=str(first_path),
        mime_type="image/png",
        file_size=first_path.stat().st_size,
        width=128,
        height=128,
        perceptual_hash=compute_phash(first_path),
        status=ProcessingStatus.COMPLETED.value,
    )
    db_session.add(first)
    db_session.commit()

    result = analyze_duplicate(second_path, image_id="img-2", db=db_session, max_distance=5)
    assert result["detected"] is True
    assert result["matched_image_id"] == "img-1"
    assert result["hamming_distance"] == 0
    assert result["similarity"] == 1.0


def test_duplicate_ignores_different_images(tmp_path, db_session):
    first_path = save_png(tmp_path / "a.png", noisy_image(seed=1))
    second_path = save_png(tmp_path / "b.png", noisy_image(seed=99))

    first = Image(
        id="img-1",
        original_filename="a.png",
        stored_filename="a.png",
        storage_path=str(first_path),
        mime_type="image/png",
        file_size=first_path.stat().st_size,
        width=128,
        height=128,
        perceptual_hash=compute_phash(first_path),
        status=ProcessingStatus.COMPLETED.value,
    )
    db_session.add(first)
    db_session.commit()

    result = analyze_duplicate(second_path, image_id="img-2", db=db_session, max_distance=5)
    assert result["detected"] is False
    assert result["matched_image_id"] is None
    assert result["hamming_distance"] is not None
    assert result["hamming_distance"] > 5


def test_phash_distance_zero_for_identical_files(tmp_path):
    path_a = save_png(tmp_path / "a.png", noisy_image(seed=7))
    path_b = save_png(tmp_path / "b.png", noisy_image(seed=7))
    assert hamming_distance(compute_phash(path_a), compute_phash(path_b)) == 0
