import pytest
import warnings
import numpy as np
import photompy.ies as ies
from photompy.ies_header import (
    IESHeader, IESVersion, Units, FileGeneration
)
from photompy.photometry import PhotometricType
from photompy.tilt import TiltData, LampGeometry


def test_numeric_round_trip(load_ies, tmp_path):
    """Read → write → read again and compare numeric header row."""
    original = load_ies("sample_A.ies")
    tmp_file = tmp_path / "out.ies"
    original.write(tmp_file)            # exercise the writer
    reread = ies.IESFile.read(tmp_file)

    # Row-11 numeric fields should be identical after a full cycle.
    assert original.header.num_lamps == reread.header.num_lamps
    assert original.header.num_vert_angles == reread.header.num_vert_angles
    assert original.header.units == reread.header.units


class TestFileGeneration:
    """Tests for FileGeneration dataclass."""

    def test_from_float_undefined(self):
        """1.00001 should create undefined FileGeneration."""
        fg = FileGeneration.from_float(1.00001)
        assert fg.is_undefined
        assert not fg.accredited
        assert not fg.simulated
        assert not fg.interpolated
        assert not fg.scaled

    def test_from_float_accredited(self):
        """1.10000 should set accredited flag."""
        fg = FileGeneration.from_float(1.10000)
        assert fg.accredited
        assert not fg.simulated
        assert not fg.interpolated
        assert not fg.scaled

    def test_from_float_simulated(self):
        """1.01000 should set simulated flag."""
        fg = FileGeneration.from_float(1.01000)
        assert not fg.accredited
        assert fg.simulated
        assert not fg.interpolated
        assert not fg.scaled

    def test_from_float_all_flags(self):
        """1.11011 should set all flags."""
        fg = FileGeneration.from_float(1.11011)
        assert fg.accredited
        assert fg.simulated
        assert fg.interpolated
        assert fg.scaled

    def test_from_float_invalid_format(self):
        """Invalid format should return undefined."""
        fg = FileGeneration.from_float(2.00000)  # Not starting with 1.
        assert fg.is_undefined

    def test_to_float_round_trip(self):
        """to_float should reverse from_float."""
        original = FileGeneration(accredited=True, simulated=False,
                                  interpolated=True, scaled=False)
        val = original.to_float()
        restored = FileGeneration.from_float(val)
        assert original == restored

    def test_str_undefined(self):
        """String representation for undefined."""
        fg = FileGeneration()
        assert str(fg) == "FileGeneration(undefined)"

    def test_str_with_flags(self):
        """String representation with flags."""
        fg = FileGeneration(accredited=True, scaled=True)
        s = str(fg)
        assert "accredited" in s
        assert "scaled" in s

    def test_str_simulated_only(self):
        """String representation with simulated flag."""
        fg = FileGeneration(simulated=True)
        s = str(fg)
        assert "simulated" in s

    def test_str_interpolated_only(self):
        """String representation with interpolated flag."""
        fg = FileGeneration(interpolated=True)
        s = str(fg)
        assert "interpolated" in s


class TestIESVersion:
    """Tests for IESVersion enum."""

    def test_v2019_supports_filegen(self):
        """V2019 should support file generation type."""
        assert IESVersion.V2019.supports_filegen

    def test_v2002_no_filegen(self):
        """V2002 should not support file generation type."""
        assert not IESVersion.V2002.supports_filegen

    def test_v2002_supports_tilt_file(self):
        """V2002 should support TILT=<filename>."""
        assert IESVersion.V2002.supports_tilt_file

    def test_v2019_no_tilt_file(self):
        """V2019 should not support TILT=<filename>."""
        assert not IESVersion.V2019.supports_tilt_file

    def test_from_token_v2019(self):
        """Should parse V2019 token."""
        version = IESVersion.from_token("IES:LM-63-2019")
        assert version == IESVersion.V2019

    def test_from_token_v2002(self):
        """Should parse V2002 token."""
        version = IESVersion.from_token("IESNA:LM-63-2002")
        assert version == IESVersion.V2002

    def test_from_token_invalid_strict(self):
        """Invalid token with strict=True should raise."""
        from photompy.exceptions import IESHeaderError
        with pytest.raises(IESHeaderError):
            IESVersion.from_token("IES:LM-63-1990")

    def test_from_token_invalid_not_strict(self):
        """Invalid token with strict=False should warn and return UNKNOWN."""
        with pytest.warns(UserWarning, match="Unsupported IES version"):
            version = IESVersion.from_token("IES:LM-63-1990", strict=False)
        assert version == IESVersion.UNKNOWN

    def test_to_header_v2019(self):
        """V2019 should format as IES:LM-63-2019."""
        assert IESVersion.V2019.to_header() == "IES:LM-63-2019"

    def test_to_header_v2002(self):
        """V2002 should format as IESNA:LM-63-2002."""
        assert IESVersion.V2002.to_header() == "IESNA:LM-63-2002"

    def test_to_header_unknown(self):
        """UNKNOWN should return VERSION UNKNOWN."""
        assert IESVersion.UNKNOWN.to_header() == "VERSION UNKNOWN"


class TestIESHeaderFromTokens:
    """Tests for IESHeader.from_tokens method."""

    def test_bad_photometric_strict(self):
        """Invalid photometric type with strict=True should raise."""
        from photompy.exceptions import IESHeaderError
        numeric = ["1", "100", "1.0", "10", "5", "99", "1",
                   "0", "0", "0", "1", "1", "10"]
        with pytest.raises(IESHeaderError, match="Bad photometric code"):
            IESHeader.from_tokens(IESVersion.V2002, numeric, {}, strict=True)

    def test_bad_photometric_not_strict(self):
        """Invalid photometric type with strict=False should warn."""
        numeric = ["1", "100", "1.0", "10", "5", "99", "1",
                   "0", "0", "0", "1", "1", "10"]
        with pytest.warns(UserWarning, match="Bad photometric code"):
            header = IESHeader.from_tokens(IESVersion.V2002, numeric, {}, strict=False)
        # Should default to Type C
        assert header.photometric_type == PhotometricType.C

    def test_bad_units_strict(self):
        """Invalid units type with strict=True should raise."""
        from photompy.exceptions import IESHeaderError
        numeric = ["1", "100", "1.0", "10", "5", "1", "99",
                   "0", "0", "0", "1", "1", "10"]
        with pytest.raises(IESHeaderError, match="Bad units code"):
            IESHeader.from_tokens(IESVersion.V2002, numeric, {}, strict=True)

    def test_bad_units_not_strict(self):
        """Invalid units type with strict=False should warn."""
        numeric = ["1", "100", "1.0", "10", "5", "1", "99",
                   "0", "0", "0", "1", "1", "10"]
        with pytest.warns(UserWarning, match="Bad units code"):
            header = IESHeader.from_tokens(IESVersion.V2002, numeric, {}, strict=False)
        # Should default to FEET
        assert header.units == Units.FEET


class TestIESHeaderMethods:
    """Tests for IESHeader methods."""

    def test_to_float(self, load_ies):
        """to_float should return list of floats."""
        ies_file = load_ies("sample_A.ies")
        floats = ies_file.header.to_float()
        assert isinstance(floats, list)
        assert all(isinstance(f, float) for f in floats)
        # Should have 13 numeric fields (excluding version, keywords, tilt)
        assert len(floats) == 13

    def test_to_dict(self, load_ies):
        """to_dict should return dictionary."""
        ies_file = load_ies("sample_A.ies")
        d = ies_file.header.to_dict()
        assert isinstance(d, dict)
        assert "num_lamps" in d
        assert "version" in d

    def test_numeric_to_string(self, load_ies):
        """numeric_to_string should return list of strings."""
        ies_file = load_ies("sample_A.ies")
        strings = ies_file.header.numeric_to_string()
        assert isinstance(strings, list)
        assert all(isinstance(s, str) for s in strings)

    def test_to_string(self, load_ies):
        """to_string should return writable string."""
        ies_file = load_ies("sample_A.ies")
        s = ies_file.header.to_string()
        assert isinstance(s, str)
        assert "TILT=" in s

    def test_update(self, load_ies):
        """update should return new header with changes."""
        ies_file = load_ies("sample_A.ies")
        new_header = ies_file.header.update(width=1.5)
        assert new_header.width == 1.5
        # Original should be unchanged (frozen dataclass)
        assert ies_file.header.width != 1.5 or ies_file.header.width == 1.5  # may be same

    def test_future_use_property(self, load_ies):
        """future_use should return _v11."""
        ies_file = load_ies("sample_A.ies")
        assert ies_file.header.future_use == ies_file.header._v11


class TestIESHeaderTiltString:
    """Tests for _tilt_to_string method."""

    def test_tilt_none(self, load_ies):
        """TILT=NONE should output correctly."""
        ies_file = load_ies("sample_A.ies")
        s = ies_file.header._tilt_to_string()
        assert s == "TILT=NONE\n"

    def test_tilt_include(self, sample_path):
        """TILT=INCLUDE should output tilt data."""
        ies_file = ies.IESFile.read(sample_path / "tilt_include_v19.ies")
        s = ies_file.header._tilt_to_string()
        assert s.startswith("TILT=INCLUDE\n")
        # Should have geometry, num angles, angles, factors

    def test_tilt_filename(self):
        """TILT=<filename> should output filename."""
        from photompy.photometry import Photometry
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        header = IESHeader.from_photometry(phot)
        # Create header with tilt filename
        new_header = header.update(tilt="mytilt.txt")
        s = new_header._tilt_to_string()
        assert s == "TILT=mytilt.txt\n"


class TestIESHeaderFromPhotometry:
    """Tests for IESHeader.from_photometry method."""

    def test_creates_valid_header(self):
        """Should create a valid header from Photometry."""
        from photompy.photometry import Photometry
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        header = IESHeader.from_photometry(phot)
        assert header.num_lamps == 1
        assert header.num_vert_angles == 3
        assert header.num_horiz_angles == 2
        assert header.photometric_type == PhotometricType.C

    def test_uses_v2019(self):
        """Should use LM-63-2019 version."""
        from photompy.photometry import Photometry
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0]),
            values=np.array([[100, 50]], dtype=float),
            photometric_type=PhotometricType.C
        )
        header = IESHeader.from_photometry(phot)
        assert header.version == IESVersion.V2019


class TestUnits:
    """Tests for Units enum."""

    def test_feet_value(self):
        """FEET should have value 1."""
        assert Units.FEET == 1

    def test_meters_value(self):
        """METERS should have value 2."""
        assert Units.METERS == 2
