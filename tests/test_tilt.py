"""Tests for TILT=INCLUDE support (LM-63 Annex F)."""
import pytest
import numpy as np
from pathlib import Path

from photompy import IESFile
from photompy.tilt import TiltData, LampGeometry


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "data"


class TestTiltData:
    """Tests for TiltData dataclass."""

    def test_basic_creation(self):
        tilt = TiltData(
            geometry=LampGeometry.VERTICAL_BASE_UP,
            angles=np.array([0, 45, 90]),
            factors=np.array([1.0, 0.9, 0.75]),
        )
        assert tilt.geometry == LampGeometry.VERTICAL_BASE_UP
        assert len(tilt.angles) == 3
        assert len(tilt.factors) == 3

    def test_geometry_from_int(self):
        """Geometry can be created from int."""
        tilt = TiltData(
            geometry=2,
            angles=[0, 90],
            factors=[1.0, 0.8],
        )
        assert tilt.geometry == LampGeometry.HORIZONTAL

    def test_arrays_converted(self):
        """Lists are converted to numpy arrays."""
        tilt = TiltData(
            geometry=1,
            angles=[0, 45, 90],
            factors=[1.0, 0.9, 0.8],
        )
        assert isinstance(tilt.angles, np.ndarray)
        assert isinstance(tilt.factors, np.ndarray)

    def test_length_mismatch_raises(self):
        """Different length angles and factors raises ValueError."""
        with pytest.raises(ValueError, match="same length"):
            TiltData(
                geometry=1,
                angles=[0, 45, 90],
                factors=[1.0, 0.9],  # Missing one
            )

    def test_get_factor_at_grid_point(self):
        tilt = TiltData(
            geometry=1,
            angles=np.array([0, 45, 90]),
            factors=np.array([1.0, 0.9, 0.75]),
        )
        assert tilt.get_factor(0) == 1.0
        assert tilt.get_factor(45) == 0.9
        assert tilt.get_factor(90) == 0.75

    def test_get_factor_interpolated(self):
        tilt = TiltData(
            geometry=1,
            angles=np.array([0, 90]),
            factors=np.array([1.0, 0.5]),
        )
        # Linear interpolation: 45 degrees should give 0.75
        assert abs(tilt.get_factor(45) - 0.75) < 0.001

    def test_from_lines(self):
        lines = [
            "1",
            "5",
            "0 22.5 45 67.5 90",
            "1.0 0.95 0.88 0.78 0.65",
        ]
        tilt = TiltData.from_lines(lines)
        assert tilt.geometry == LampGeometry.VERTICAL_BASE_UP
        assert len(tilt.angles) == 5
        assert len(tilt.factors) == 5
        assert tilt.angles[0] == 0
        assert tilt.angles[-1] == 90
        assert tilt.factors[0] == 1.0

    def test_from_lines_insufficient_raises(self):
        with pytest.raises(ValueError, match="Expected 4 lines"):
            TiltData.from_lines(["1", "3"])

    def test_from_lines_angle_count_mismatch_raises(self):
        lines = [
            "1",
            "5",  # Says 5 angles
            "0 45 90",  # Only 3 angles
            "1.0 0.9 0.8",
        ]
        with pytest.raises(ValueError, match="Expected 5 angles"):
            TiltData.from_lines(lines)

    def test_to_lines(self):
        tilt = TiltData(
            geometry=LampGeometry.HORIZONTAL,
            angles=np.array([0, 45, 90]),
            factors=np.array([1.0, 0.9, 0.8]),
        )
        lines = tilt.to_lines()
        assert len(lines) == 4
        assert lines[0] == "2"  # HORIZONTAL geometry
        assert lines[1] == "3"  # count
        assert "45" in lines[2]
        assert "0.9" in lines[3]

    def test_equality(self):
        tilt1 = TiltData(1, [0, 90], [1.0, 0.8])
        tilt2 = TiltData(1, [0, 90], [1.0, 0.8])
        tilt3 = TiltData(2, [0, 90], [1.0, 0.8])
        assert tilt1 == tilt2
        assert tilt1 != tilt3


class TestLampGeometry:
    """Tests for LampGeometry enum."""

    def test_values(self):
        assert LampGeometry.VERTICAL_BASE_UP == 1
        assert LampGeometry.HORIZONTAL == 2
        assert LampGeometry.TILTS_WITH_LUMINAIRE == 3

    def test_from_int(self):
        assert LampGeometry(1) == LampGeometry.VERTICAL_BASE_UP
        assert LampGeometry(2) == LampGeometry.HORIZONTAL
        assert LampGeometry(3) == LampGeometry.TILTS_WITH_LUMINAIRE


class TestTiltIncludeRead:
    """Tests for reading TILT=INCLUDE files."""

    def test_read_tilt_include_v19(self, sample_path):
        ies = IESFile.read(sample_path / "tilt_include_v19.ies")
        assert isinstance(ies.header.tilt, TiltData)
        assert ies.header.tilt.geometry == LampGeometry.VERTICAL_BASE_UP
        assert len(ies.header.tilt.angles) == 7
        assert ies.header.tilt.angles[0] == 0
        assert ies.header.tilt.angles[-1] == 90

    def test_read_tilt_include_geometry2(self, sample_path):
        ies = IESFile.read(sample_path / "tilt_include_geometry2.ies")
        assert isinstance(ies.header.tilt, TiltData)
        assert ies.header.tilt.geometry == LampGeometry.HORIZONTAL
        assert len(ies.header.tilt.angles) == 13

    def test_read_tilt_include_geometry3(self, sample_path):
        ies = IESFile.read(sample_path / "tilt_include_geometry3.ies")
        assert isinstance(ies.header.tilt, TiltData)
        assert ies.header.tilt.geometry == LampGeometry.TILTS_WITH_LUMINAIRE

    def test_read_tilt_none(self, sample_path):
        ies = IESFile.read(sample_path / "sample_A.ies")
        assert ies.header.tilt == "NONE"


class TestTiltIncludeWrite:
    """Tests for writing TILT=INCLUDE files."""

    def test_write_tilt_none(self, sample_path, tmp_path):
        """TILT=NONE files write correctly."""
        ies = IESFile.read(sample_path / "sample_A.ies")
        outfile = tmp_path / "output.ies"
        ies.write(outfile)

        reread = IESFile.read(outfile)
        assert reread.header.tilt == "NONE"

    def test_write_tilt_include(self, sample_path, tmp_path):
        """TILT=INCLUDE data is preserved on write."""
        ies = IESFile.read(sample_path / "tilt_include_v19.ies")
        outfile = tmp_path / "output.ies"
        ies.write(outfile)

        reread = IESFile.read(outfile)
        assert isinstance(reread.header.tilt, TiltData)
        assert reread.header.tilt.geometry == ies.header.tilt.geometry
        np.testing.assert_array_almost_equal(
            reread.header.tilt.angles, ies.header.tilt.angles
        )
        np.testing.assert_array_almost_equal(
            reread.header.tilt.factors, ies.header.tilt.factors
        )


class TestTiltIncludeRoundTrip:
    """Round-trip tests for TILT=INCLUDE."""

    def test_round_trip_geometry1(self, sample_path, tmp_path):
        original = IESFile.read(sample_path / "tilt_include_v19.ies")
        outfile = tmp_path / "roundtrip.ies"
        original.write(outfile)

        reread = IESFile.read(outfile)
        assert reread.header.tilt == original.header.tilt

    def test_round_trip_geometry2(self, sample_path, tmp_path):
        original = IESFile.read(sample_path / "tilt_include_geometry2.ies")
        outfile = tmp_path / "roundtrip.ies"
        original.write(outfile)

        reread = IESFile.read(outfile)
        assert reread.header.tilt == original.header.tilt

    def test_round_trip_preserves_photometry(self, sample_path, tmp_path):
        """Photometry data is preserved alongside TILT data."""
        original = IESFile.read(sample_path / "tilt_include_v19.ies")
        outfile = tmp_path / "roundtrip.ies"
        original.write(outfile)

        reread = IESFile.read(outfile)
        np.testing.assert_array_almost_equal(
            reread.photometry.values, original.photometry.values, decimal=2
        )
