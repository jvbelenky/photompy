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

    def test_to_dict(self, sample_path):
        """to_dict should return a dictionary representation."""
        # Note: must use path (not file handle) for to_dict to work
        ies = IESFile.read(sample_path / "sample_A.ies")
        d = ies.to_dict()
        assert isinstance(d, dict)
        assert "header" in d
        assert "photometry" in d

    def test_total(self, load_ies):
        """total should return total optical power."""
        ies = load_ies("sample_A.ies")
        total = ies.total()
        assert total > 0


class TestIESFileFromPhotometry:
    """Tests for creating IESFile from Photometry."""

    def test_from_photometry(self):
        """Can create IESFile from standalone Photometry."""
        from photompy.photometry import Photometry, PhotometricType
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        ies = IESFile.from_photometry(phot)
        assert ies.photometry is phot
        assert ies.header is not None

    def test_from_photometry_header_defaults(self):
        """Header should have sensible defaults."""
        from photompy.photometry import Photometry, PhotometricType
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        ies = IESFile.from_photometry(phot)
        assert ies.header.num_lamps == 1
        assert ies.header.multiplier == 1.0

    def test_from_photometry_write(self, tmp_path):
        """IESFile from Photometry should be writable."""
        from photompy.photometry import Photometry, PhotometricType
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        ies = IESFile.from_photometry(phot)
        outfile = tmp_path / "from_phot.ies"
        ies.write(outfile)
        assert outfile.exists()


class TestIESFileUpdate:
    """Tests for IESFile update method."""

    def test_update_width(self, load_ies):
        """Can update header fields."""
        ies = load_ies("sample_A.ies")
        ies.update(width=0.5)
        assert ies.header.width == 0.5

    def test_update_multiple(self, load_ies):
        """Can update multiple header fields."""
        ies = load_ies("sample_A.ies")
        ies.update(width=0.5, length=0.3)
        assert ies.header.width == 0.5
        assert ies.header.length == 0.3

    def test_update_multiplier_raises(self, load_ies):
        """Updating multiplier to non-1 should raise."""
        ies = load_ies("sample_A.ies")
        with pytest.raises(ValueError, match="multiplier"):
            ies.update(multiplier=2.0)


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

    def test_write_full(self, load_ies, tmp_path):
        """Write with which='full' should expand angles."""
        ies = load_ies("sample_A.ies")
        outpath = tmp_path / "full.ies"
        ies.write(outpath, which="full")
        assert outpath.exists()

        reread = IESFile.read(outpath)
        # Full should have more phis
        assert len(reread.photometry.phis) >= len(ies.photometry.phis)

    def test_write_interp(self, load_ies, tmp_path):
        """Write with which='interp' should interpolate."""
        ies = load_ies("sample_A.ies")
        outpath = tmp_path / "interp.ies"
        ies.write(outpath, which="interp", interp_args=(91, 181))
        assert outpath.exists()

        reread = IESFile.read(outpath)
        assert len(reread.photometry.thetas) == 91
        assert len(reread.photometry.phis) == 181

    def test_write_precision(self, load_ies, tmp_path):
        """Write with custom precision."""
        ies = load_ies("sample_A.ies")
        outpath = tmp_path / "precision.ies"
        ies.write(outpath, precision=4)
        assert outpath.exists()


class TestIESFileScalingMethods:
    """Additional scaling method tests."""

    def test_scale_to_total(self, load_ies):
        """scale_to_total should set total optical power."""
        ies = load_ies("sample_A.ies")
        ies.scale_to_total(1000)
        assert np.isclose(ies.total(), 1000, rtol=0.01)

    def test_scale_to_center(self, load_ies):
        """scale_to_center should set center value."""
        ies = load_ies("sample_A.ies")
        ies.scale_to_center(500)
        assert np.isclose(ies.center(), 500)


class TestIESFileAttributePassthrough:
    """Test that attributes are passed through to header/photometry."""

    def test_passthrough_to_photometry(self, load_ies):
        """Should pass through photometry attributes."""
        ies = load_ies("sample_A.ies")
        # These come from photometry
        assert ies.thetas is ies.photometry.thetas
        assert ies.phis is ies.photometry.phis

    def test_passthrough_to_header(self, load_ies):
        """Should pass through header attributes."""
        ies = load_ies("sample_A.ies")
        # These come from header
        assert ies.num_lamps == ies.header.num_lamps

    def test_unknown_attribute_raises(self, load_ies):
        """Unknown attributes should raise AttributeError."""
        ies = load_ies("sample_A.ies")
        with pytest.raises(AttributeError):
            _ = ies.nonexistent_attribute


class TestIESFilePlot:
    """Tests for IESFile.plot method."""

    @pytest.mark.skip(reason="Slow due to matplotlib startup")
    def test_plot_polar(self, load_ies):
        """plot with polar type should work."""
        import matplotlib.pyplot as plt
        ies_file = load_ies("sample_A.ies")
        ies_file.plot(plot_type="polar")
        plt.close('all')

    @pytest.mark.skip(reason="Slow due to matplotlib startup")
    def test_plot_cartesian(self, load_ies):
        """plot with cartesian type should work."""
        import matplotlib.pyplot as plt
        ies_file = load_ies("sample_A.ies")
        ies_file.plot(plot_type="cartesian")
        plt.close('all')

    def test_plot_invalid_type_raises(self, load_ies):
        """plot with invalid type should raise ValueError."""
        ies_file = load_ies("sample_A.ies")
        with pytest.raises(ValueError, match="unrecognized plot type"):
            ies_file.plot(plot_type="invalid")


class TestIESFileGetPhotometry:
    """Tests for IESFile._get_photometry method."""

    def test_get_orig_photometry(self, load_ies):
        """_get_photometry with 'orig' returns original photometry."""
        ies_file = load_ies("sample_A.ies")
        phot = ies_file._get_photometry("orig")
        assert phot is ies_file.photometry

    def test_get_full_photometry(self, load_ies):
        """_get_photometry with 'full' returns expanded photometry."""
        ies_file = load_ies("sample_A.ies")
        phot = ies_file._get_photometry("full")
        # Should be expanded
        assert len(phot.phis) >= len(ies_file.photometry.phis)

    def test_get_interp_photometry(self, load_ies):
        """_get_photometry with 'interp' returns interpolated photometry."""
        ies_file = load_ies("sample_A.ies")
        phot = ies_file._get_photometry("interp", (91, 181))
        assert len(phot.thetas) == 91
        assert len(phot.phis) == 181

    def test_get_invalid_mode_raises(self, load_ies):
        """_get_photometry with invalid mode raises ValueError."""
        ies_file = load_ies("sample_A.ies")
        with pytest.raises(ValueError, match="Unknown photometry mode"):
            ies_file._get_photometry("invalid")


class TestIESFileCheckFilename:
    """Tests for IESFile._check_filename method."""

    def test_valid_ies_extension(self, tmp_path):
        """Should not raise for .ies extension."""
        path = tmp_path / "test.ies"
        # Should not raise
        IESFile._check_filename(path)

    def test_invalid_extension_strict(self, tmp_path):
        """Should raise for non-.ies extension with strict=True."""
        from photompy.exceptions import IESPathError
        path = tmp_path / "test.txt"
        with pytest.raises(IESPathError, match="Unexpected extension"):
            IESFile._check_filename(path, strict=True)

    def test_invalid_extension_not_strict(self, tmp_path):
        """Should warn for non-.ies extension with strict=False."""
        path = tmp_path / "test.txt"
        with pytest.warns(UserWarning, match="Unexpected extension"):
            IESFile._check_filename(path, strict=False)


class TestIESFileSplitString:
    """Tests for IESFile._split_string method."""

    def test_tilt_filename(self):
        """Should parse TILT=<filename> format."""
        ies_string = """IES:LM-63-2019
[TEST] Test
TILT=mytilt.dat
1 100 1.0 3 2 1 1 0 0 0 1 1 10
0 45 90
0 180
100 80 50 100 80 50"""
        version, header, tilt, numeric, blocks = IESFile._split_string(ies_string)
        assert tilt == "mytilt.dat"

    def test_missing_tilt_raises(self):
        """Should raise IESHeaderError if TILT line is missing."""
        from photompy.exceptions import IESHeaderError
        ies_string = """IES:LM-63-2019
[TEST] Test
1 100 1.0 3 2 1 1 0 0 0 1 1 10
0 45 90
0 180
100 80 50 100 80 50"""
        with pytest.raises(IESHeaderError, match="TILT= line missing"):
            IESFile._split_string(ies_string)
