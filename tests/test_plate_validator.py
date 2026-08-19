from app.analyzers.plate_validator import (
    find_plate_candidates,
    normalize_plate_text,
    validate_indian_plate,
)


def test_standard_plates_are_format_valid():
    for plate in ("KA01AB1234", "MH12CD5678", "DL01AA1234", "DL1CAA1234"):
        result = validate_indian_plate(plate)
        assert result["format_valid"] is True, plate
        assert result["matched_value"] == plate
        assert result["matched_pattern"] == "standard"


def test_standard_plate_with_spaces_is_format_valid():
    result = validate_indian_plate("KA 01 AB 1234")
    assert result["format_valid"] is True
    assert result["matched_value"] == "KA01AB1234"
    assert result["matched_pattern"] == "standard"


def test_standard_plate_with_hyphens_is_format_valid():
    result = validate_indian_plate("KA-01-AB-1234")
    assert result["format_valid"] is True
    assert result["matched_value"] == "KA01AB1234"
    assert result["matched_pattern"] == "standard"


def test_bharat_series_is_format_valid():
    result = validate_indian_plate("22BH1234AA")
    assert result["format_valid"] is True
    assert result["matched_value"] == "22BH1234AA"
    assert result["matched_pattern"] == "bharat_series"


def test_bharat_series_with_spaces_is_format_valid():
    result = validate_indian_plate("22 BH 1234 AA")
    assert result["format_valid"] is True
    assert result["matched_value"] == "22BH1234AA"
    assert result["matched_pattern"] == "bharat_series"


def test_bharat_series_with_hyphens_is_format_valid():
    result = validate_indian_plate("22-BH-1234-AA")
    assert result["format_valid"] is True
    assert result["matched_value"] == "22BH1234AA"
    assert result["matched_pattern"] == "bharat_series"


def test_normalizes_spaces_and_hyphens():
    result = validate_indian_plate("ka-01-ab-1234")
    assert normalize_plate_text("ka-01-ab-1234") == "KA01AB1234"
    assert result["format_valid"] is True
    assert result["matched_value"] == "KA01AB1234"


def test_finds_plate_inside_ocr_sentence():
    text = "Vehicle registration KA01AB1234 detected"
    result = validate_indian_plate(text)
    assert result["format_valid"] is True
    assert result["matched_value"] == "KA01AB1234"
    assert result["matched_pattern"] == "standard"
    assert ("KA01AB1234", "standard") in find_plate_candidates(text)


def test_finds_bharat_series_inside_ocr_sentence():
    result = validate_indian_plate("Vehicle 22BH1234AA detected")
    assert result["format_valid"] is True
    assert result["matched_value"] == "22BH1234AA"
    assert result["matched_pattern"] == "bharat_series"


def test_finds_standard_plate_in_normal_ocr_sentence():
    result = validate_indian_plate(
        "Vehicle registration number: KA01AB1234 detected successfully"
    )
    assert result["format_valid"] is True
    assert result["matched_value"] == "KA01AB1234"
    assert result["matched_pattern"] == "standard"


def test_weekday_date_is_not_a_vehicle_number():
    result = validate_indian_plate("Tuesday, 17 Feb 2026")
    assert result["format_valid"] is False
    assert result["matched_value"] is None
    assert result["matched_pattern"] is None


def test_hyphenated_date_is_not_a_vehicle_number():
    result = validate_indian_plate("17-Feb-2026")
    assert result["format_valid"] is False
    assert result["matched_value"] is None
    assert result["matched_pattern"] is None


def test_ocr_date_text_does_not_fabricate_a_plate():
    text = "Tuesday, 17 Feb 2026 11:22 AM"
    result = validate_indian_plate(text)
    assert result["format_valid"] is False
    assert result["matched_value"] is None
    assert result["matched_pattern"] is None
    candidates = find_plate_candidates(text)
    assert candidates == []
    assert "AY17FEB2026" not in (value for value, _pattern in candidates)


def test_address_ocr_text_is_not_a_vehicle_number():
    result = validate_indian_plate(
        "Perambur High Road, Chennai, Tamil Nadu 600011"
    )
    assert result["format_valid"] is False
    assert result["matched_value"] is None
    assert result["matched_pattern"] is None


def test_observed_ocr_dump_does_not_fabricate_ay17feb2026():
    text = (
        "DrAga auospitl Baer isi i 550) oy co Ss Tuesday, 17 Feb 2026 "
        "11:22 AM mq Perambur High Road, CMWSSB Division 70, Perambur, "
        "Ward 70, Zone 6 Thiru. Vi. Ka. Nagar, Chennai Corporation, "
        "Chennai, Tamil Nadu, 600011, India Lat: 13.1059115 | "
        "Long: 80.2514811 TASK ID: 22FUGV4G2K igelcig"
    )
    result = validate_indian_plate(text)
    assert result["format_valid"] is False
    assert result["matched_value"] is None
    assert result["matched_pattern"] is None
    assert result["matched_value"] != "AY17FEB2026"
    assert "AY17FEB2026" not in (
        value for value, _pattern in find_plate_candidates(text)
    )


def test_concatenated_date_token_is_not_a_vehicle_number():
    result = validate_indian_plate("TUESDAY17FEB2026")
    assert result["format_valid"] is False
    assert result["matched_value"] is None


def test_invalid_text_is_not_format_valid():
    result = validate_indian_plate("HELLO WORLD")
    assert result["format_valid"] is False
    assert result["matched_value"] is None
    assert result["matched_pattern"] is None


def test_empty_ocr_is_not_format_valid():
    result = validate_indian_plate(None)
    assert result["format_valid"] is False
    assert result["matched_value"] is None
    assert result["matched_pattern"] is None
    assert result["confidence"] == 0.0


def test_blank_ocr_string_is_not_format_valid():
    result = validate_indian_plate("")
    assert result["format_valid"] is False
    assert result["matched_value"] is None
    assert result["matched_pattern"] is None
    assert result["confidence"] == 0.0
