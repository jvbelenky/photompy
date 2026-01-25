"""Edge case and error handling tests."""
import pytest
import numpy as np
from photompy.ies import IESFile
from photompy.photometry import Photometry, PhotometricType, LampSymmetry
from photompy.exceptions import IESDataError


class TestBoundaryConditions:
    def test_single_theta(self):
        """Single theta angle should work."""
        phot = Photometry(
            thetas=np.array([0]),
            phis=np.array([0, 180]),
            values=np.array([[100], [100]]),
            photometric_type=PhotometricType.C
        )
        assert phot.max() == 100

    def test_single_phi(self):
        """Single phi angle (AXIAL symmetry) should work."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0]),
            values=np.array([[100, 50]]),
            photometric_type=PhotometricType.C
        )
        assert phot.symmetry == LampSymmetry.AXIAL

    def test_two_thetas(self):
        """Two theta angles should work."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 50], [100, 50]]),
            photometric_type=PhotometricType.C
        )
        val = phot.get_intensity(45, 90)
        assert np.isfinite(val)

    def test_two_phis(self):
        """Two phi angles should work."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]]),
            photometric_type=PhotometricType.C
        )
        val = phot.get_intensity(45, 90)
        assert np.isfinite(val)


class TestValueRanges:
    def test_zero_values(self):
        """All-zero values should work."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 180]),
            values=np.zeros((2, 2)),
            photometric_type=PhotometricType.C
        )
        assert phot.max() == 0
        assert phot.center() == 0

    def test_uniform_values(self):
        """Uniform non-zero values should work."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 90, 180]),
            values=np.ones((3, 3)) * 500,
            photometric_type=PhotometricType.C
        )
        assert phot.max() == 500
        val = phot.get_intensity(22.5, 45)
        assert val == 500

    def test_very_small_values(self):
        """Very small values should work."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 180]),
            values=np.array([[1e-10, 1e-10], [1e-10, 1e-10]]),
            photometric_type=PhotometricType.C
        )
        assert phot.max() == pytest.approx(1e-10)

    def test_very_large_values(self):
        """Very large values should work."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 180]),
            values=np.array([[1e10, 1e10], [1e10, 1e10]]),
            photometric_type=PhotometricType.C
        )
        assert phot.max() == pytest.approx(1e10)


class TestSymmetryDetection:
    def test_full_360_is_none_symmetry(self):
        """Full 0-360 range should be NONE symmetry."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 90, 180, 270, 360]),
            values=np.ones((5, 2)),
            photometric_type=PhotometricType.C
        )
        assert phot.symmetry == LampSymmetry.NONE

    def test_180_range_is_half_symmetry(self):
        """0-180 range should be HALF symmetry."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 90, 180]),
            values=np.ones((3, 2)),
            photometric_type=PhotometricType.C
        )
        assert phot.symmetry == LampSymmetry.HALF

    def test_90_range_is_quad_symmetry(self):
        """0-90 range should be QUAD symmetry."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 45, 90]),
            values=np.ones((3, 2)),
            photometric_type=PhotometricType.C
        )
        assert phot.symmetry == LampSymmetry.QUAD

    def test_single_phi_is_axial(self):
        """Single phi should be AXIAL symmetry."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0]),
            values=np.ones((1, 2)),
            photometric_type=PhotometricType.C
        )
        assert phot.symmetry == LampSymmetry.AXIAL


class TestInterpolationEdgeCases:
    def test_interpolate_at_boundary_theta_0(self):
        """Interpolation at theta=0 boundary."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]]),
            photometric_type=PhotometricType.C
        )
        val = phot.get_intensity(0, 0)
        assert val == 100

    def test_interpolate_at_boundary_theta_max(self):
        """Interpolation at maximum theta boundary."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]]),
            photometric_type=PhotometricType.C
        )
        val = phot.get_intensity(90, 0)
        assert val == 20

    def test_interpolate_at_phi_0(self):
        """Interpolation at phi=0."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 180, 360]),
            values=np.array([[100, 50], [80, 40], [100, 50]]),
            photometric_type=PhotometricType.C
        )
        val = phot.get_intensity(45, 0)
        assert np.isfinite(val)

    def test_interpolate_at_phi_360(self):
        """Interpolation at phi=360 should equal phi=0."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 180, 360]),
            values=np.array([[100, 50], [80, 40], [100, 50]]),
            photometric_type=PhotometricType.C
        )
        v1 = phot.get_intensity(45, 0)
        v2 = phot.get_intensity(45, 360)
        np.testing.assert_allclose(v1, v2)


class TestScalingEdgeCases:
    def test_scale_by_zero_raises(self, simple_photometry):
        """Scaling by zero should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            simple_photometry.scale(0)

    def test_scale_by_negative_raises(self, simple_photometry):
        """Scaling by negative should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            simple_photometry.scale(-1)

    def test_scale_to_max_zero_values(self):
        """scale_to_max on zero values produces NaN (divide by zero)."""
        phot = Photometry(
            thetas=np.array([0, 90]),
            phis=np.array([0, 180]),
            values=np.zeros((2, 2)),
            photometric_type=PhotometricType.C
        )
        # Dividing by zero max produces NaN
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            phot.scale_to_max(100)
        assert np.all(np.isnan(phot.values))


class TestFileReadEdgeCases:
    def test_read_all_sample_files(self, sample_path):
        """All sample files should be readable."""
        ies_files = list(sample_path.glob("*.ies"))
        assert len(ies_files) > 0

        for ies_file in ies_files:
            try:
                ies = IESFile.read(ies_file)
                assert ies.photometry is not None
            except Exception as e:
                pytest.fail(f"Failed to read {ies_file.name}: {e}")
