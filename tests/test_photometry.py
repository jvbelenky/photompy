"""Tests for Photometry class."""
import numpy as np
import pytest
import photompy.interpolate as interp
from photompy.photometry import Photometry, PhotometricType, LampSymmetry
from photompy.exceptions import IESDataError


class TestPhotometryInit:
    def test_basic_creation(self, simple_photometry):
        assert simple_photometry.photometric_type == PhotometricType.C
        assert len(simple_photometry.thetas) == 4
        assert len(simple_photometry.phis) == 2

    def test_shape_mismatch_raises(self):
        with pytest.raises(IESDataError):
            Photometry(
                thetas=np.array([0, 90]),
                phis=np.array([0, 180]),
                values=np.array([[100]]),  # Wrong shape
                photometric_type=PhotometricType.C
            )

    def test_values_shape_matches_angles(self, simple_photometry):
        assert simple_photometry.values.shape == (
            len(simple_photometry.phis),
            len(simple_photometry.thetas)
        )


class TestSymmetryInference:
    def test_axial_symmetry(self, axial_photometry):
        assert axial_photometry.symmetry == LampSymmetry.AXIAL

    def test_quad_symmetry(self, quad_photometry):
        assert quad_photometry.symmetry == LampSymmetry.QUAD

    def test_half_symmetry(self, half_photometry):
        assert half_photometry.symmetry == LampSymmetry.HALF

    def test_none_symmetry(self, full_photometry):
        assert full_photometry.symmetry == LampSymmetry.NONE


class TestExpandAngles:
    def test_axial_expansion(self, axial_photometry):
        expanded = axial_photometry.expanded()
        # AXIAL expands to 360 phi values
        assert len(expanded.phis) >= 360

    def test_quad_expansion(self, quad_photometry):
        expanded = quad_photometry.expanded()
        # Should cover full range
        assert expanded.phis[-1] >= 270

    def test_half_expansion(self, half_photometry):
        """Test HALF symmetry expansion (this was the critical bug fix)."""
        expanded = half_photometry.expanded()
        assert len(expanded.phis) > len(half_photometry.phis)
        assert expanded.phis[-1] >= 270

    def test_none_expansion_unchanged(self, full_photometry):
        expanded = full_photometry.expanded()
        np.testing.assert_array_equal(expanded.phis, full_photometry.phis)
        np.testing.assert_array_equal(expanded.values, full_photometry.values)


class TestGetIntensity:
    def test_at_grid_point(self, simple_photometry):
        val = simple_photometry.get_intensity(0, 0)
        assert val == 100

    def test_interpolated_point(self, simple_photometry):
        val = simple_photometry.get_intensity(15, 45)
        assert 0 < val < 100

    def test_boundary_theta(self, simple_photometry):
        val = simple_photometry.get_intensity(90, 0)
        assert val == 10

    def test_phi_wrap(self, full_photometry):
        v1 = full_photometry.get_intensity(90, 0)
        v2 = full_photometry.get_intensity(90, 360)
        np.testing.assert_allclose(v1, v2)

    def test_out_of_range_theta_raises(self, simple_photometry):
        with pytest.raises(ValueError):
            simple_photometry.get_intensity(200, 0)

    def test_negative_theta_raises(self, simple_photometry):
        with pytest.raises(ValueError):
            simple_photometry.get_intensity(-10, 0)

    def test_array_input(self, simple_photometry):
        thetas = np.array([0, 30, 60])
        phis = np.array([0, 0, 0])
        vals = simple_photometry.get_intensity(thetas, phis)
        assert vals.shape == (3,)
        np.testing.assert_allclose(vals, [100, 80, 40])


class TestScaling:
    def test_scale_to_max(self, simple_photometry):
        simple_photometry.scale_to_max(50)
        assert simple_photometry.max() == 50

    def test_scale_to_center(self, simple_photometry):
        simple_photometry.scale_to_center(200)
        assert simple_photometry.center() == 200

    def test_scale_factor(self, simple_photometry):
        original_max = simple_photometry.max()
        simple_photometry.scale(2.0)
        assert simple_photometry.max() == original_max * 2


class TestCaching:
    def test_expanded_cached(self, simple_photometry):
        exp1 = simple_photometry.expanded()
        exp2 = simple_photometry.expanded()
        assert exp1 is exp2  # Same object

    def test_interpolated_cached(self, simple_photometry):
        int1 = simple_photometry.interpolated(10, 20)
        int2 = simple_photometry.interpolated(10, 20)
        assert int1 is int2

    def test_different_interp_params_different_cache(self, simple_photometry):
        int1 = simple_photometry.interpolated(10, 20)
        int2 = simple_photometry.interpolated(20, 40)
        assert int1 is not int2


class TestEquality:
    def test_equal_photometry(self, simple_photometry):
        other = Photometry(
            thetas=simple_photometry.thetas.copy(),
            phis=simple_photometry.phis.copy(),
            values=simple_photometry.values.copy(),
            photometric_type=simple_photometry.photometric_type
        )
        assert simple_photometry == other

    def test_different_values_not_equal(self, simple_photometry):
        other = Photometry(
            thetas=simple_photometry.thetas.copy(),
            phis=simple_photometry.phis.copy(),
            values=simple_photometry.values.copy() * 2,
            photometric_type=simple_photometry.photometric_type
        )
        assert simple_photometry != other


class TestLegacyInterpolate:
    """Test that Photometry.get_intensity matches legacy interpolate.get_intensity."""

    def test_intensity_interpolation(self, load_ies):
        ies_file = load_ies("sample_B.ies")
        phot = ies_file.photometry
        theta, phi = 22.5, 135.0
        v1 = phot.get_intensity(theta, phi)
        valdict = {"thetas": phot.thetas, "phis": phot.phis, "values": phot.values}
        v2 = interp.get_intensity(theta, phi, valdict)
        np.testing.assert_allclose(v1, v2, rtol=1e-6)


class TestDivisionByZeroProtection:
    """Test that interpolation handles duplicate angles gracefully."""

    def test_duplicate_thetas(self):
        """When consecutive thetas are identical, should not raise ZeroDivisionError."""
        phot = Photometry(
            thetas=np.array([0, 0, 45, 90]),  # Duplicate at start
            phis=np.array([0, 180]),
            values=np.array([
                [100, 100, 70, 20],
                [100, 100, 70, 20],
            ]),
            photometric_type=PhotometricType.C
        )
        val = phot.get_intensity(0, 0)
        assert np.isfinite(val)

    def test_duplicate_phis(self):
        """When consecutive phis are identical, should not raise ZeroDivisionError."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 0, 90, 180]),  # Duplicate at start
            values=np.array([
                [100, 70, 20],
                [100, 70, 20],
                [100, 65, 18],
                [100, 60, 15],
            ]),
            photometric_type=PhotometricType.C
        )
        val = phot.get_intensity(45, 0)
        assert np.isfinite(val)
