"""Tests for read.py module."""
import pytest
import numpy as np
import warnings
from pathlib import Path
from photompy._read import (
    load_bytes, get_version, process_keywords, process_header,
    read_angles, verify_valdict
)
from photompy.legacy import read_ies_data


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
        # Note: TILT is now handled separately by IESFile._split_string
        header = [
            "[TEST] Test Value",
            "[MANUFAC] Company",
        ]
        result = process_keywords(header)
        assert result["TEST"] == "Test Value"
        assert result["MANUFAC"] == "Company"

    def test_tilt_not_in_keywords(self):
        # TILT is now handled separately and should not be in keywords
        header = [
            "[TEST] Test",
        ]
        result = process_keywords(header)
        assert "TILT" not in result

    def test_empty_value(self):
        header = [
            "[EMPTY]",
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


class TestLoadBytesExtended:
    """Additional load_bytes tests for coverage."""

    def test_load_from_bytearray(self):
        """Should handle bytearray input."""
        data = bytearray(b"IESNA:LM-63-2002\nTILT=NONE\n")
        raw, origin = load_bytes(data)
        assert isinstance(raw, bytes)
        assert origin is None

    def test_load_from_string_with_tilt(self):
        """Should treat string containing TILT= as in-memory IES data."""
        ies_string = "IESNA:LM-63-2002\nTILT=NONE\n1 100 1 3 1 1 1 0 0 0 1 1 10\n0 45 90\n0\n100 80 50"
        raw, origin = load_bytes(ies_string)
        assert isinstance(raw, bytes)
        assert origin is None
        assert b"TILT=NONE" in raw

    def test_load_invalid_type_raises(self):
        """Should raise TypeError for invalid input."""
        with pytest.raises(TypeError, match="Cannot interpret"):
            load_bytes(12345)

    def test_load_from_file_handle(self, sample_path):
        """Should handle file-like objects."""
        with open(sample_path / "sample_A.ies", "r") as f:
            raw, origin = load_bytes(f)
        assert isinstance(raw, bytes)
        assert origin is None


class TestGetLampType:
    """Tests for get_lamp_type function."""
    from photompy._read import get_lamp_type

    def test_type_c_axial(self):
        """Type C with single phi (axial symmetry)."""
        from photompy._read import get_lamp_type
        phis = np.array([0])
        result = get_lamp_type(phis, 1)
        assert result == "C0"

    def test_type_c_quad(self):
        """Type C with phis ending at 90 (quad symmetry)."""
        from photompy._read import get_lamp_type
        phis = np.array([0, 45, 90])
        result = get_lamp_type(phis, 1)
        assert result == "C90"

    def test_type_c_half(self):
        """Type C with phis ending at 180 (half symmetry)."""
        from photompy._read import get_lamp_type
        phis = np.array([0, 90, 180])
        result = get_lamp_type(phis, 1)
        assert result == "C180"

    def test_type_c_full(self):
        """Type C with phis ending at 360 (full)."""
        from photompy._read import get_lamp_type
        phis = np.array([0, 90, 180, 270, 360])
        result = get_lamp_type(phis, 1)
        assert result == "C360"

    def test_type_c_bad_first_phi_warns(self):
        """Type C with non-zero first phi should warn."""
        from photompy._read import get_lamp_type
        phis = np.array([10, 90, 180])
        with pytest.warns(UserWarning, match="first horizontal"):
            get_lamp_type(phis, 1)

    def test_type_c_bad_last_phi_warns(self):
        """Type C with invalid last phi should warn."""
        from photompy._read import get_lamp_type
        phis = np.array([0, 45, 120])  # 120 is not valid
        with pytest.warns(UserWarning, match="last horizontal"):
            get_lamp_type(phis, 1)

    def test_type_b_quad(self):
        """Type B with 0 to 90 (quad symmetry)."""
        from photompy._read import get_lamp_type
        phis = np.array([0, 45, 90])
        with pytest.warns(UserWarning, match="not currently supported"):
            result = get_lamp_type(phis, 2)
        assert result == "B0"

    def test_type_b_half(self):
        """Type B with -90 to 90 (half symmetry)."""
        from photompy._read import get_lamp_type
        phis = np.array([-90, 0, 90])
        with pytest.warns(UserWarning, match="not currently supported"):
            result = get_lamp_type(phis, 2)
        assert result == "B-90"

    def test_type_b_bad_last_phi_warns(self):
        """Type B with last phi not 90 should warn."""
        from photompy._read import get_lamp_type
        phis = np.array([0, 45, 60])
        with pytest.warns(UserWarning, match="last horizontal"):
            get_lamp_type(phis, 2)

    def test_type_b_bad_first_phi_warns(self):
        """Type B with first phi not -90 or 0 should warn."""
        from photompy._read import get_lamp_type
        phis = np.array([-45, 0, 90])
        with pytest.warns(UserWarning, match="first horizontal"):
            get_lamp_type(phis, 2)

    def test_type_a_quad(self):
        """Type A with 0 to 90 (quad symmetry)."""
        from photompy._read import get_lamp_type
        phis = np.array([0, 45, 90])
        with pytest.warns(UserWarning, match="not currently supported"):
            result = get_lamp_type(phis, 3)
        assert result == "A0"

    def test_type_a_half(self):
        """Type A with -90 to 90 (half symmetry)."""
        from photompy._read import get_lamp_type
        phis = np.array([-90, 0, 90])
        with pytest.warns(UserWarning, match="not currently supported"):
            result = get_lamp_type(phis, 3)
        assert result == "A-90"

    def test_unknown_photometry_warns(self):
        """Unknown photometry type should warn."""
        from photompy._read import get_lamp_type
        phis = np.array([0, 90])
        with pytest.warns(UserWarning, match="could not be determined"):
            result = get_lamp_type(phis, 99)
        assert result == "?"


class TestFormatAngles:
    """Tests for _format_angles function."""
    from photompy._read import _format_angles

    def test_c90_symmetry(self, sample_path):
        """Test C90 (quad) symmetry expansion."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_B.ies", interpolate=False)

        # sample_B may have different symmetry; let's test manually
        if lampdict["photometry"] == "C90":
            full = lampdict["full_vals"]
            # C90 expands to 4 quadrants
            assert len(full["phis"]) > len(lampdict["original_vals"]["phis"])

    def test_theta_extension_to_180(self, sample_path):
        """Test that thetas ending at 90 get extended to 180."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies", interpolate=False)

        orig_thetas = lampdict["original_vals"]["thetas"]
        full_thetas = lampdict["full_vals"]["thetas"]

        if orig_thetas[-1] == 90:
            # Should extend to 180
            assert full_thetas[-1] >= 180


class TestProcessKeywordsExtended:
    """Additional process_keywords tests."""

    def test_more_lines_combined(self):
        """MORE lines should be combined with previous keyword."""
        header = [
            "[LUMINAIRE] Long description",
            "[MORE] that continues here",
            "[MORE] and here too",
            "[TEST] Another value",
        ]
        result = process_keywords(header)
        assert "LUMINAIRE" in result
        assert "that continues here" in result["LUMINAIRE"]
        assert "and here too" in result["LUMINAIRE"]
        assert result["TEST"] == "Another value"

    def test_duplicate_keys_renamed(self):
        """Duplicate keys (except MORE) should get numbered."""
        header = [
            "[CUSTOM] First",
            "[CUSTOM] Second",
            "[CUSTOM] Third",
        ]
        result = process_keywords(header)
        assert "CUSTOM-1" in result
        assert "CUSTOM-2" in result
        assert "CUSTOM-3" in result
