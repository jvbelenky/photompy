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


class TestTotalOpticalPower:
    """Tests for total optical power calculation."""

    def test_total_method(self, simple_photometry):
        """total() should return same as total_optical_power()."""
        total = simple_photometry.total()
        top = simple_photometry.total_optical_power()
        assert total == top

    def test_total_positive(self, simple_photometry):
        """Total optical power should be positive for non-zero values."""
        total = simple_photometry.total()
        assert total > 0

    def test_total_zero_values(self):
        """Zero values should give zero total."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.zeros((2, 3)),
            photometric_type=PhotometricType.C
        )
        assert phot.total() == 0


class TestFingerprint:
    """Tests for photometry fingerprinting."""

    def test_fingerprint_returns_bytes(self, simple_photometry):
        """Fingerprint should return bytes."""
        fp = simple_photometry.to_fingerprint()
        assert isinstance(fp, bytes)
        assert len(fp) == 20  # SHA1 produces 20 bytes

    def test_same_data_same_fingerprint(self):
        """Identical photometry should have same fingerprint."""
        phot1 = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        phot2 = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        assert phot1.to_fingerprint() == phot2.to_fingerprint()

    def test_different_data_different_fingerprint(self):
        """Different photometry should have different fingerprint."""
        phot1 = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        phot2 = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 21], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        assert phot1.to_fingerprint() != phot2.to_fingerprint()


class TestCoords:
    """Tests for coordinate generation."""

    def test_coords_cached(self, simple_photometry):
        """coords should be cached."""
        _ = simple_photometry.expanded()  # Prime expansion cache
        c1 = simple_photometry.coords
        c2 = simple_photometry.coords
        assert c1 is c2

    def test_coords_shape(self, simple_photometry):
        """coords should have correct shape."""
        exp = simple_photometry.expanded()
        coords = simple_photometry.coords
        n_points = len(exp.thetas) * len(exp.phis)
        assert coords.shape == (n_points, 3)

    def test_photometric_coords_cached(self, simple_photometry):
        """photometric_coords should be cached."""
        _ = simple_photometry.expanded()
        pc1 = simple_photometry.photometric_coords
        pc2 = simple_photometry.photometric_coords
        assert pc1 is pc2


class TestScalingWithCache:
    """Tests for scaling when cache has expanded photometry."""

    def test_scale_updates_cached_expanded(self, simple_photometry):
        """Scaling should update cached expanded photometry."""
        _ = simple_photometry.expanded()
        original_max = simple_photometry.max()
        simple_photometry.scale(2.0)

        # Main values should be scaled
        assert np.isclose(simple_photometry.max(), original_max * 2)

        # Cached expanded should also be scaled
        exp = simple_photometry.expanded()
        assert np.isclose(exp.max(), original_max * 2)

    def test_scale_to_max_updates_cache(self, simple_photometry):
        """scale_to_max should update cached photometry."""
        _ = simple_photometry.expanded()
        simple_photometry.scale_to_max(500)
        assert np.isclose(simple_photometry.max(), 500)

    def test_scale_to_total_updates_cache(self, simple_photometry):
        """scale_to_total should update cached photometry."""
        _ = simple_photometry.expanded()
        simple_photometry.scale_to_total(1000)
        assert np.isclose(simple_photometry.total(), 1000, rtol=0.01)

    def test_scale_to_center_updates_cache(self, simple_photometry):
        """scale_to_center should update cached photometry."""
        _ = simple_photometry.expanded()
        simple_photometry.scale_to_center(500)
        assert np.isclose(simple_photometry.center(), 500)


class TestPhotometryEquality:
    """Additional equality tests."""

    def test_different_photometric_type_not_equal(self):
        """Different photometric types should not be equal."""
        phot_c = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 45, 90]),
            values=np.ones((3, 3)) * 100,
            photometric_type=PhotometricType.C
        )
        phot_b = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 45, 90]),
            values=np.ones((3, 3)) * 100,
            photometric_type=PhotometricType.B
        )
        assert phot_c != phot_b

    def test_different_symmetry_not_equal(self):
        """Different symmetries should not be equal."""
        phot_axial = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0]),  # Single phi = axial
            values=np.array([[100, 70, 20]]),
            photometric_type=PhotometricType.C
        )
        phot_quad = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 45, 90]),  # 0-90 = quad
            values=np.ones((3, 3)) * 100,
            photometric_type=PhotometricType.C
        )
        assert phot_axial != phot_quad

    def test_not_equal_to_non_photometry(self, simple_photometry):
        """Photometry should not equal non-Photometry objects."""
        assert simple_photometry != "not a photometry"
        assert simple_photometry != 42
        assert simple_photometry != None
