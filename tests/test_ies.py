"""Tests for IESFile class."""
import pytest
import copy
import numpy as np
from photompy.ies import IESFile


class TestIESFileRead:
    def test_read_from_path(self, sample_path):
        ies = IESFile.read(sample_path / "sample_A.ies")
        assert ies.header is not None
        assert ies.photometry is not None

    def test_read_from_file_handle(self, sample_path):
        with open(sample_path / "sample_A.ies", "r") as f:
            ies = IESFile.read(f)
        assert ies.photometry is not None

    def test_read_sample_b(self, sample_path):
        """Test reading a different sample file."""
        ies = IESFile.read(sample_path / "sample_B.ies")
        assert ies.header is not None
        assert ies.photometry is not None
        assert len(ies.photometry.thetas) > 0

    def test_header_attributes(self, load_ies):
        ies = load_ies("sample_A.ies")
        assert hasattr(ies.header, 'num_lamps')
        assert hasattr(ies.header, 'num_vert_angles')
        assert hasattr(ies.header, 'num_horiz_angles')

    def test_photometry_attributes(self, load_ies):
        ies = load_ies("sample_A.ies")
        assert hasattr(ies.photometry, 'thetas')
        assert hasattr(ies.photometry, 'phis')
        assert hasattr(ies.photometry, 'values')


class TestIESFileWrite:
    def test_write_to_file(self, load_ies, tmp_path):
        ies = load_ies("sample_A.ies")
        outpath = tmp_path / "written.ies"
        ies.write(outpath)
        assert outpath.exists()

    def test_write_returns_bytes(self, load_ies):
        ies = load_ies("sample_A.ies")
        result = ies.write(filename=None)
        assert isinstance(result, bytes)

    def test_round_trip_preserves_photometry(self, load_ies, tmp_path):
        original = load_ies("sample_A.ies")
        outpath = tmp_path / "roundtrip.ies"
        original.write(outpath)
        reread = IESFile.read(outpath)

        np.testing.assert_array_almost_equal(
            original.photometry.thetas,
            reread.photometry.thetas,
            decimal=2
        )
        np.testing.assert_array_almost_equal(
            original.photometry.phis,
            reread.photometry.phis,
            decimal=2
        )


class TestIESFileScaling:
    def test_scale_to_max(self, load_ies):
        ies = load_ies("sample_A.ies")
        ies.scale_to_max(100)
        assert ies.photometry.max() == 100

    def test_scale(self, load_ies):
        ies = load_ies("sample_A.ies")
        original_max = ies.photometry.max()
        ies.scale(2.0)
        np.testing.assert_allclose(ies.photometry.max(), original_max * 2)


class TestIESFileEquality:
    def test_equal_files(self, load_ies):
        ies1 = load_ies("sample_A.ies")
        ies2 = load_ies("sample_A.ies")
        assert ies1 == ies2

    def test_different_files(self, load_ies):
        ies1 = load_ies("sample_A.ies")
        ies2 = load_ies("sample_B.ies")
        assert ies1 != ies2

    def test_deepcopy(self, load_ies):
        ies = load_ies("sample_A.ies")
        copied = copy.deepcopy(ies)
        assert ies == copied
        copied.scale(2.0)
        assert ies != copied


class TestIESFileMethods:
    def test_max(self, load_ies):
        ies = load_ies("sample_A.ies")
        max_val = ies.max()
        assert max_val == ies.photometry.max()
        assert max_val > 0

    def test_center(self, load_ies):
        ies = load_ies("sample_A.ies")
        center_val = ies.center()
        assert center_val == ies.photometry.center()

    def test_expanded(self, load_ies):
        ies = load_ies("sample_A.ies")
        expanded = ies.expanded()
        assert expanded is not None
        # Expanded should have more or equal phis
        assert len(expanded.phis) >= len(ies.photometry.phis)

    def test_interpolated(self, load_ies):
        ies = load_ies("sample_A.ies")
        interpolated = ies.interpolated(num_thetas=91, num_phis=181)
        assert len(interpolated.thetas) == 91
        assert len(interpolated.phis) == 181
