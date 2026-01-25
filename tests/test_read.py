"""Tests for read.py module."""
import pytest
import numpy as np
import warnings
from pathlib import Path
from photompy.read import (
    load_bytes, get_version, process_keywords, process_header,
    read_angles, verify_valdict, read_ies_data
)


class TestLoadBytes:
    def test_load_from_path(self, sample_path):
        raw, origin = load_bytes(sample_path / "sample_A.ies")
        assert isinstance(raw, bytes)
        assert b"IESNA" in raw or b"IES" in raw
        assert origin == sample_path / "sample_A.ies"

    def test_load_from_bytes(self):
        data = b"IESNA:LM-63-2002\nTILT=NONE\n"
        raw, origin = load_bytes(data)
        assert raw == data
        assert origin is None

    def test_load_from_string_path(self, sample_path):
        path_str = str(sample_path / "sample_A.ies")
        raw, origin = load_bytes(path_str)
        assert isinstance(raw, bytes)

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            load_bytes(Path("/nonexistent/file.ies"))


class TestGetVersion:
    def test_lm63_2002_version(self):
        lines = ["IESNA:LM-63-2002", "other"]
        assert get_version(lines) == "IESNA:LM-63-2002"

    def test_lm63_1995_version(self):
        lines = ["IESNA:LM-63-1995", "other"]
        assert get_version(lines) == "IESNA:LM-63-1995"

    def test_iesna_91_version(self):
        lines = ["IESNA91", "other"]
        assert get_version(lines) == "IESNA91"

    def test_missing_version_warns(self):
        lines = ["[TEST] something", "TILT=NONE"]
        with pytest.warns(UserWarning):
            version = get_version(lines)
        assert version == "Not specified"


class TestProcessKeywords:
    def test_basic_keywords(self):
        header = [
            "[TEST] Test Value",
            "[MANUFAC] Company",
            "TILT=NONE"
        ]
        result = process_keywords(header)
        assert result["TEST"] == "Test Value"
        assert result["MANUFAC"] == "Company"
        assert result["TILT"] == "NONE"

    def test_tilt_include(self):
        header = [
            "[TEST] Test",
            "TILT=INCLUDE"
        ]
        result = process_keywords(header)
        assert result["TILT"] == "INCLUDE"

    def test_empty_value(self):
        header = [
            "[EMPTY]",
            "TILT=NONE"
        ]
        result = process_keywords(header)
        assert result["EMPTY"] == ""


class TestProcessHeader:
    def test_numeric_parsing(self):
        data = ["1", "100.0", "1.0", "37", "17", "1", "1",
                "0.05", "0.05", "0", "1", "1", "12.6"]
        result = process_header(data)
        assert result["num_lamps"] == 1
        assert result["lumens_per_lamp"] == 100.0
        assert result["multiplier"] == 1.0
        assert result["num_vertical_angles"] == 37
        assert result["num_horizontal_angles"] == 17
        assert result["photometric_type"] == 1
        assert result["units_type"] == 1
        assert result["width"] == 0.05
        assert result["length"] == 0.05
        assert result["height"] == 0
        assert result["ballast_factor"] == 1
        assert result["future_use"] == 1
        assert result["input_watts"] == 12.6


class TestReadAngles:
    def test_basic_angles(self):
        data = ["0", "45", "90", "0", "180", "100", "80", "50", "100", "80", "50"]
        thetas, phis, values = read_angles(data, 3, 2)
        np.testing.assert_array_equal(thetas, [0, 45, 90])
        np.testing.assert_array_equal(phis, [0, 180])
        assert values.shape == (2, 3)
        np.testing.assert_array_equal(values[0], [100, 80, 50])
        np.testing.assert_array_equal(values[1], [100, 80, 50])

    def test_single_phi(self):
        data = ["0", "90", "0", "100", "50"]
        thetas, phis, values = read_angles(data, 2, 1)
        np.testing.assert_array_equal(thetas, [0, 90])
        np.testing.assert_array_equal(phis, [0])
        assert values.shape == (1, 2)


class TestVerifyValdict:
    def test_valid_valdict(self):
        valdict = {
            "thetas": np.array([0, 90]),
            "phis": np.array([0]),
            "values": np.array([[100, 50]])
        }
        verify_valdict(valdict)  # Should not raise

    def test_missing_key_raises(self):
        valdict = {"thetas": np.array([0]), "phis": np.array([0])}
        with pytest.raises(KeyError):
            verify_valdict(valdict)

    def test_shape_mismatch_raises(self):
        valdict = {
            "thetas": np.array([0, 90]),
            "phis": np.array([0, 180]),
            "values": np.array([[100]])  # Wrong shape
        }
        with pytest.raises(ValueError):
            verify_valdict(valdict)


class TestReadIesData:
    def test_read_sample_file(self, sample_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies")

        assert "version" in lampdict
        assert "keywords" in lampdict
        assert "original_vals" in lampdict
        assert "full_vals" in lampdict

    def test_read_without_extend(self, sample_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            # Must also disable interpolate since it depends on full_vals
            lampdict = read_ies_data(sample_path / "sample_A.ies", extend=False, interpolate=False)

        assert "original_vals" in lampdict
        assert "full_vals" not in lampdict

    def test_read_without_interpolate(self, sample_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies", interpolate=False)

        assert "interp_vals" not in lampdict

    def test_deprecation_warning(self, sample_path):
        with pytest.warns(DeprecationWarning, match="read_ies_data is deprecated"):
            read_ies_data(sample_path / "sample_A.ies")
