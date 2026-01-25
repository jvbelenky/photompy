"""Tests for interpolate.py module."""
import pytest
import numpy as np
import warnings
from photompy.interpolate import interpolate_values, get_intensity
from photompy.read import read_ies_data


class TestGetIntensity:
    @pytest.fixture
    def sample_valdict(self):
        return {
            "thetas": np.array([0, 45, 90]),
            "phis": np.array([0, 180, 360]),
            "values": np.array([
                [100, 70, 30],
                [100, 70, 30],
                [100, 70, 30],
            ])
        }

    def test_at_grid_point(self, sample_valdict):
        val = get_intensity(0, 0, sample_valdict)
        assert val == 100

    def test_at_grid_point_theta_45(self, sample_valdict):
        val = get_intensity(45, 0, sample_valdict)
        assert val == 70

    def test_at_grid_point_theta_90(self, sample_valdict):
        val = get_intensity(90, 180, sample_valdict)
        assert val == 30

    def test_interpolated_theta(self, sample_valdict):
        val = get_intensity(22.5, 0, sample_valdict)
        # Midpoint between 0 and 45 degrees, values 100 and 70
        expected = (100 + 70) / 2
        np.testing.assert_allclose(val, expected, rtol=0.01)

    def test_interpolated_phi(self, sample_valdict):
        val = get_intensity(0, 90, sample_valdict)
        # Midpoint between phi=0 and phi=180, both have value 100
        assert val == 100

    def test_out_of_range_theta_raises(self, sample_valdict):
        with pytest.raises(ValueError):
            get_intensity(200, 0, sample_valdict)

    def test_negative_theta_raises(self, sample_valdict):
        with pytest.raises(ValueError):
            get_intensity(-10, 0, sample_valdict)

    def test_phi_normalization(self, sample_valdict):
        # Phi values > 360 should be normalized
        v1 = get_intensity(45, 0, sample_valdict)
        v2 = get_intensity(45, 360, sample_valdict)
        np.testing.assert_allclose(v1, v2)

    def test_array_input(self, sample_valdict):
        thetas = np.array([0, 45, 90])
        phis = np.array([0, 0, 0])
        vals = get_intensity(thetas, phis, sample_valdict)
        np.testing.assert_array_equal(vals, [100, 70, 30])

    def test_division_by_zero_protection_thetas(self):
        """Test with duplicate theta values."""
        valdict = {
            "thetas": np.array([0, 0, 90]),  # Duplicate at start
            "phis": np.array([0, 180]),
            "values": np.array([[100, 50], [100, 50], [20, 10]])
        }
        # Should not raise ZeroDivisionError
        val = get_intensity(0, 90, valdict)
        assert np.isfinite(val)

    def test_division_by_zero_protection_phis(self):
        """Test with duplicate phi values."""
        valdict = {
            "thetas": np.array([0, 90]),
            "phis": np.array([0, 0, 180]),  # Duplicate at start
            "values": np.array([[100, 50], [100, 50], [100, 50]])
        }
        val = get_intensity(45, 0, valdict)
        assert np.isfinite(val)


class TestInterpolateValues:
    def test_creates_interp_vals(self, sample_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies", interpolate=False)

        interpolate_values(lampdict)
        assert "interp_vals" in lampdict

    def test_custom_resolution(self, sample_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies", interpolate=False)

        interpolate_values(lampdict, num_thetas=91, num_phis=181)
        assert len(lampdict["interp_vals"]["thetas"]) == 91
        assert len(lampdict["interp_vals"]["phis"]) == 181

    def test_interp_vals_shape(self, sample_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies", interpolate=False)

        interpolate_values(lampdict, num_thetas=10, num_phis=20)
        assert lampdict["interp_vals"]["values"].shape == (20, 10)

    def test_overwrite_warning(self, sample_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies", interpolate=False)

        interpolate_values(lampdict)  # First time
        with pytest.warns(UserWarning, match="already exists"):
            interpolate_values(lampdict)  # Second time without overwrite

    def test_overwrite_allowed(self, sample_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies", interpolate=False)

        interpolate_values(lampdict, num_thetas=50, num_phis=50)
        original_shape = lampdict["interp_vals"]["values"].shape

        # Overwrite with different resolution
        interpolate_values(lampdict, num_thetas=100, num_phis=100, overwrite=True)
        new_shape = lampdict["interp_vals"]["values"].shape

        assert new_shape != original_shape
        assert new_shape == (100, 100)
