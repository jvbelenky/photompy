"""Tests for calculate.py module."""
import pytest
import numpy as np
from pathlib import Path
import warnings

from photompy import total_optical_power, lamp_area
from photompy.calculate import compute_frustrum_area, _compute_total_power


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "data"


class TestTotalOpticalPower:
    """Tests for total_optical_power function."""

    def test_from_file_path(self, sample_path):
        """Calculate total power from file path."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            power = total_optical_power(sample_path / "sample_A.ies")
        assert power > 0

    def test_from_string_path(self, sample_path):
        """Calculate total power from string path."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            power = total_optical_power(str(sample_path / "sample_A.ies"))
        assert power > 0

    def test_from_valdict(self):
        """Calculate total power from value dictionary."""
        valdict = {
            "thetas": np.array([0, 45, 90, 135, 180]),
            "phis": np.array([0, 90, 180, 270]),
            "values": np.ones((4, 5)) * 1000,
        }
        power = total_optical_power(valdict)
        assert power > 0

    def test_invalid_input_raises(self):
        """Invalid input should raise ValueError."""
        with pytest.raises(ValueError, match="must be either"):
            total_optical_power(12345)

    def test_custom_resolution(self, sample_path):
        """Can specify custom theta/phi resolution."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            power = total_optical_power(
                sample_path / "sample_A.ies",
                num_thetas=91,
                num_phis=181
            )
        assert power > 0


class TestComputeFrustrumArea:
    """Tests for compute_frustrum_area function."""

    def test_hemisphere(self):
        """Full hemisphere should be 2*pi."""
        area = compute_frustrum_area(0, 90)
        assert np.isclose(area, 2 * np.pi)

    def test_full_sphere(self):
        """Full sphere should be 4*pi."""
        area = compute_frustrum_area(0, 180)
        assert np.isclose(area, 4 * np.pi)

    def test_zero_area(self):
        """Same angles should give zero area."""
        area = compute_frustrum_area(45, 45)
        assert np.isclose(area, 0)

    def test_array_input(self):
        """Should handle array inputs."""
        theta1 = np.array([0, 45, 90])
        theta2 = np.array([45, 90, 135])
        areas = compute_frustrum_area(theta1, theta2)
        assert len(areas) == 3
        assert all(a > 0 for a in areas)


class TestComputeTotalPower:
    """Tests for _compute_total_power function."""

    def test_uniform_distribution(self):
        """Uniform distribution should integrate correctly."""
        valdict = {
            "thetas": np.linspace(0, 180, 181),
            "phis": np.linspace(0, 360, 361),
            "values": np.ones((361, 181)) * 1000,  # 1000 cd uniform
        }
        power = _compute_total_power(valdict)
        # Uniform 1000 cd over 4*pi steradians = 4000*pi lumens
        expected = 1000 * 4 * np.pi
        assert np.isclose(power, expected, rtol=0.01)


class TestLampArea:
    """Tests for lamp_area function."""

    def test_meters(self, sample_path):
        """Get area in meters."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            area = lamp_area(sample_path / "sample_A.ies", units="meters")
        assert area >= 0

    def test_feet(self, sample_path):
        """Get area in feet."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            area = lamp_area(sample_path / "sample_A.ies", units="feet")
        assert area >= 0

    def test_inches(self, sample_path):
        """Get area in inches."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            area = lamp_area(sample_path / "sample_A.ies", units="inches")
        assert area >= 0

    def test_invalid_units_raises(self, sample_path):
        """Invalid units should raise KeyError."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(KeyError, match="must be either"):
                lamp_area(sample_path / "sample_A.ies", units="lightyears")

    def test_unit_conversion(self, sample_path):
        """Area in feet should be larger than meters."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            area_m = lamp_area(sample_path / "sample_A.ies", units="meters")
            area_ft = lamp_area(sample_path / "sample_A.ies", units="feet")
        # 1 m^2 = 10.764 ft^2
        if area_m > 0:
            ratio = area_ft / area_m
            assert np.isclose(ratio, 1 / (0.3048 ** 2), rtol=0.01)


class TestLampAreaUnitsType:
    """Tests for lamp_area with different unit types."""

    def test_file_with_meters_units(self, tmp_path, sample_path):
        """Test file with units_type=2 (meters)."""
        # Read a sample file and change units_type to 2
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from photompy.read import read_ies_data
            from photompy.write import write_ies_data
            lampdict = read_ies_data(sample_path / "sample_A.ies")

        # Change units_type to meters (2)
        lampdict["units_type"] = 2

        # Write to new file
        outfile = tmp_path / "meters_units.ies"
        write_ies_data(lampdict, filename=outfile)

        # Now test lamp_area with this file
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            area_m = lamp_area(outfile, units="meters")
            area_ft = lamp_area(outfile, units="feet")

        # Should get valid results
        assert area_m >= 0
        assert area_ft >= 0


class TestLoadInterpdict:
    """Tests for _load_interpdict function."""

    def test_loads_existing_interp_vals(self, sample_path):
        """Should return interp_vals from already interpolated dict."""
        from photompy.calculate import _load_interpdict
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            valdict = _load_interpdict(sample_path / "sample_A.ies", 91, 181)
        assert "thetas" in valdict
        assert "phis" in valdict
        assert "values" in valdict
