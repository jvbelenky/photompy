"""Tests for Type A and Type B photometry support."""
import pytest
import numpy as np
from pathlib import Path

from photompy import IESFile
from photompy.photometry import Photometry, PhotometricType, LampSymmetry


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "data"


class TestPhotometricType:
    """Tests for PhotometricType enum."""

    def test_values(self):
        assert PhotometricType.C == 1
        assert PhotometricType.B == 2
        assert PhotometricType.A == 3

    def test_from_int(self):
        assert PhotometricType(1) == PhotometricType.C
        assert PhotometricType(2) == PhotometricType.B
        assert PhotometricType(3) == PhotometricType.A


class TestTypeBRead:
    """Tests for reading Type B photometry files."""

    def test_read_type_b_symmetric(self, sample_path):
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        assert ies.photometry.photometric_type == PhotometricType.B
        assert ies.photometry.symmetry == LampSymmetry.QUAD

    def test_read_type_b_full(self, sample_path):
        """Type B file with full V range (-90 to 90) but symmetric H (0 to 90)."""
        ies = IESFile.read(sample_path / "type_b_full.ies")
        assert ies.photometry.photometric_type == PhotometricType.B
        # H angles are 0 to 90, so it's QUAD symmetric for H
        assert ies.photometry.symmetry == LampSymmetry.QUAD
        # V angles are -90 to 90 (full range)
        assert ies.photometry.thetas[0] == -90
        assert ies.photometry.thetas[-1] == 90

    def test_type_b_angles(self, sample_path):
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        # Vertical angles should be 0 to 90
        assert ies.photometry.thetas[0] == 0
        assert ies.photometry.thetas[-1] == 90
        # Horizontal angles should be 0 to 90
        assert ies.photometry.phis[0] == 0
        assert ies.photometry.phis[-1] == 90


class TestTypeARead:
    """Tests for reading Type A photometry files."""

    def test_read_type_a_symmetric(self, sample_path):
        ies = IESFile.read(sample_path / "type_a_symmetric.ies")
        assert ies.photometry.photometric_type == PhotometricType.A
        assert ies.photometry.symmetry == LampSymmetry.QUAD


class TestTypeBExpansion:
    """Tests for Type B photometry expansion."""

    def test_expand_type_b_symmetric(self, sample_path):
        """Type B with 0-90 H angles should expand to -90 to 90."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        expanded = ies.photometry.expanded()

        # H angles should be mirrored
        assert expanded.phis[0] == -90
        assert expanded.phis[-1] == 90

        # V angles should also be mirrored
        assert expanded.thetas[0] == -90
        assert expanded.thetas[-1] == 90

    def test_expand_type_b_full(self, sample_path):
        """Type B with symmetric H angles (0-90) should expand H to -90 to 90."""
        ies = IESFile.read(sample_path / "type_b_full.ies")
        expanded = ies.photometry.expanded()

        # H angles should be mirrored from 0-90 to -90 to 90
        assert expanded.phis[0] == -90
        assert expanded.phis[-1] == 90
        # V angles were already -90 to 90, should remain unchanged
        assert expanded.thetas[0] == -90
        assert expanded.thetas[-1] == 90

    def test_expand_preserves_center_value(self, sample_path):
        """Center value should be preserved during expansion."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        original_center = ies.photometry.values[0, 0]  # H=0, V=0

        expanded = ies.photometry.expanded()
        # Find center in expanded
        center_phi_idx = np.argmin(np.abs(expanded.phis))
        center_theta_idx = np.argmin(np.abs(expanded.thetas))
        expanded_center = expanded.values[center_phi_idx, center_theta_idx]

        assert np.isclose(original_center, expanded_center)


class TestTypeAExpansion:
    """Tests for Type A photometry expansion."""

    def test_expand_type_a_symmetric(self, sample_path):
        """Type A with 0-90 H angles should expand to -90 to 90."""
        ies = IESFile.read(sample_path / "type_a_symmetric.ies")
        expanded = ies.photometry.expanded()

        # H angles should be mirrored
        assert expanded.phis[0] == -90
        assert expanded.phis[-1] == 90


class TestTypeBIntensity:
    """Tests for Type B intensity interpolation."""

    def test_get_intensity_at_grid_point(self, sample_path):
        """Should get exact value at grid point."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        # Note: get_intensity uses theta (vertical) and phi (horizontal)
        # For Type B, theta corresponds to V and phi to H
        intensity = ies.photometry.get_intensity(theta=0, phi=0)
        expected = ies.photometry.values[0, 0]
        assert np.isclose(intensity, expected)


class TestTypeBRoundTrip:
    """Round-trip tests for Type B photometry."""

    def test_round_trip_type_b_symmetric(self, sample_path, tmp_path):
        """Type B file should survive read-write-read cycle."""
        original = IESFile.read(sample_path / "type_b_symmetric.ies")
        outfile = tmp_path / "roundtrip.ies"
        original.write(outfile)

        reread = IESFile.read(outfile)
        assert reread.photometry.photometric_type == PhotometricType.B
        np.testing.assert_array_almost_equal(
            reread.photometry.values, original.photometry.values, decimal=2
        )

    def test_round_trip_type_b_full(self, sample_path, tmp_path):
        """Type B with full H range should survive round-trip."""
        original = IESFile.read(sample_path / "type_b_full.ies")
        outfile = tmp_path / "roundtrip.ies"
        original.write(outfile)

        reread = IESFile.read(outfile)
        assert reread.photometry.photometric_type == PhotometricType.B
        np.testing.assert_array_almost_equal(
            reread.photometry.values, original.photometry.values, decimal=2
        )


class TestTypeARoundTrip:
    """Round-trip tests for Type A photometry."""

    def test_round_trip_type_a(self, sample_path, tmp_path):
        """Type A file should survive read-write-read cycle."""
        original = IESFile.read(sample_path / "type_a_symmetric.ies")
        outfile = tmp_path / "roundtrip.ies"
        original.write(outfile)

        reread = IESFile.read(outfile)
        assert reread.photometry.photometric_type == PhotometricType.A
        np.testing.assert_array_almost_equal(
            reread.photometry.values, original.photometry.values, decimal=2
        )


class TestTypeBManual:
    """Manual tests for Type B photometry creation."""

    def test_create_type_b_photometry(self):
        """Can create Type B photometry manually."""
        thetas = np.array([0, 45, 90])  # V angles
        phis = np.array([0, 45, 90])  # H angles
        values = np.array([
            [100, 80, 50],  # H=0
            [90, 70, 40],  # H=45
            [80, 60, 30],  # H=90
        ], dtype=float)

        phot = Photometry(
            thetas=thetas,
            phis=phis,
            values=values,
            photometric_type=PhotometricType.B,
        )

        assert phot.photometric_type == PhotometricType.B
        assert phot.symmetry == LampSymmetry.QUAD

    def test_expand_manual_type_b(self):
        """Manual Type B photometry can be expanded."""
        thetas = np.array([0, 45, 90])
        phis = np.array([0, 45, 90])
        values = np.array([
            [100, 80, 50],
            [90, 70, 40],
            [80, 60, 30],
        ], dtype=float)

        phot = Photometry(
            thetas=thetas,
            phis=phis,
            values=values,
            photometric_type=PhotometricType.B,
        )

        expanded = phot.expanded()
        assert expanded.thetas[0] == -90
        assert expanded.thetas[-1] == 90
        assert expanded.phis[0] == -90
        assert expanded.phis[-1] == 90


class TestTypeBInterpolation:
    """Tests for Type B interpolation."""

    def test_interpolate_type_b_symmetric(self, sample_path):
        """Type B interpolation should use -90 to 90 range."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        interp = ies.photometry.interpolated(num_thetas=91, num_phis=91)

        # Should use Type B ranges
        assert interp.thetas[0] == -90
        assert interp.thetas[-1] == 90
        assert interp.phis[0] == -90
        assert interp.phis[-1] == 90

    def test_interpolate_type_b_preserves_type(self, sample_path):
        """Interpolated Type B should remain Type B."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        interp = ies.photometry.interpolated(num_thetas=91, num_phis=91)
        assert interp.photometric_type == PhotometricType.B

    def test_interpolate_type_b_center_value(self, sample_path):
        """Center value should be preserved after interpolation."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        original_center = ies.photometry.get_intensity(0, 0)

        interp = ies.photometry.interpolated(num_thetas=91, num_phis=91)
        interp_center = interp.get_intensity(0, 0)

        assert np.isclose(original_center, interp_center, rtol=0.01)


class TestTypeBGetIntensity:
    """Tests for Type B get_intensity with negative angles."""

    def test_get_intensity_negative_theta(self, sample_path):
        """Should handle negative theta for expanded Type B."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        expanded = ies.photometry.expanded()

        # Should work with negative theta
        intensity = expanded.get_intensity(theta=-45, phi=0)
        assert intensity > 0

    def test_get_intensity_negative_phi(self, sample_path):
        """Should handle negative phi for expanded Type B."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        expanded = ies.photometry.expanded()

        # Should work with negative phi
        intensity = expanded.get_intensity(theta=0, phi=-45)
        assert intensity > 0

    def test_get_intensity_symmetry(self, sample_path):
        """Symmetric expansion should mirror values correctly."""
        ies = IESFile.read(sample_path / "type_b_symmetric.ies")
        expanded = ies.photometry.expanded()

        # Due to quad symmetry mirroring, values at mirrored H angles should match
        # when V angle is the same (positive V)
        i1 = expanded.get_intensity(theta=45, phi=45)
        i2 = expanded.get_intensity(theta=45, phi=-45)
        assert np.isclose(i1, i2)

        # And for negative V angle
        i3 = expanded.get_intensity(theta=-45, phi=45)
        i4 = expanded.get_intensity(theta=-45, phi=-45)
        assert np.isclose(i3, i4)


class TestTypeAInterpolation:
    """Tests for Type A interpolation."""

    def test_interpolate_type_a(self, sample_path):
        """Type A interpolation should use -90 to 90 range."""
        ies = IESFile.read(sample_path / "type_a_symmetric.ies")
        interp = ies.photometry.interpolated(num_thetas=91, num_phis=91)

        assert interp.thetas[0] == -90
        assert interp.thetas[-1] == 90
        assert interp.phis[0] == -90
        assert interp.phis[-1] == 90
        assert interp.photometric_type == PhotometricType.A
