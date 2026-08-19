from pathlib import Path

from app.analyzers.common import compute_downscale_size, downscale_bgr, load_bgr
from app.core.config import settings
from app.services.image_preprocess_service import prepare_processing_image
from tests.helpers import save_png, solid_image


def test_compute_downscale_size_preserves_aspect_ratio():
    assert compute_downscale_size(3200, 2400, 1600) == (1600, 1200)
    assert compute_downscale_size(800, 600, 1600) is None
    assert compute_downscale_size(2400, 3200, 1600) == (1200, 1600)


def test_downscale_bgr_does_not_enlarge_small_image(tmp_path):
    image = load_bgr(save_png(tmp_path / "small.png", solid_image((400, 300), (10, 10, 10))))
    result = downscale_bgr(image, 1600)
    assert result.shape == image.shape


def test_prepare_processing_image_downscales_large_input(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAX_PROCESSING_DIMENSION", 800)
    monkeypatch.setattr(settings, "WORKER_TEMP_PATH", str(tmp_path / "worker-temp"))

    source = save_png(tmp_path / "large.png", solid_image((2400, 1800), (120, 80, 40)))
    with prepare_processing_image(source) as processing_path:
        assert processing_path != source
        assert processing_path.suffix == ".jpg"
        image = load_bgr(processing_path)
        height, width = image.shape[:2]
        assert max(width, height) == 800
        assert width == 800
        assert height == 600

    assert not (tmp_path / "worker-temp" / f"{source.stem}_proc.jpg").exists()


def test_prepare_processing_image_keeps_small_input(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAX_PROCESSING_DIMENSION", 1600)
    monkeypatch.setattr(settings, "WORKER_TEMP_PATH", str(tmp_path / "worker-temp"))

    source = save_png(tmp_path / "small.png", solid_image((640, 480), (50, 50, 50)))
    with prepare_processing_image(source) as processing_path:
        assert processing_path == source

    assert not any((tmp_path / "worker-temp").glob("*")) if (tmp_path / "worker-temp").exists() else True


def test_prepare_processing_image_cleans_up_temp_file_on_error(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAX_PROCESSING_DIMENSION", 400)
    monkeypatch.setattr(settings, "WORKER_TEMP_PATH", str(tmp_path / "worker-temp"))

    source = save_png(tmp_path / "large.png", solid_image((1600, 1200), (30, 30, 30)))
    dest = tmp_path / "worker-temp" / f"{source.stem}_proc.jpg"

    try:
        with prepare_processing_image(source):
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert not dest.exists()
