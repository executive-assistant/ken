"""Unit tests for OCR helper logic."""

from cassey.tools.ocr_tool import choose_ocr_method


def test_choose_ocr_method_structured():
    method = choose_ocr_method("Extract receipt items as JSON", 100)
    assert method == "vision"


def test_choose_ocr_method_large_file():
    method = choose_ocr_method("Extract all text", 800)
    assert method == "local"


def test_choose_ocr_method_default():
    method = choose_ocr_method("Extract text", 50)
    assert method == "local"
