"""Tests for LDTFile class (EULUMDAT format)."""
import pytest
import copy
import numpy as np
from photompy.ldt import LDTFile, LDTHeader, LDTLampSet
from photompy.photometry import Photometry, PhotometricType, LampSymmetry
from photompy.exceptions import LDTPathError


class TestLDTFileRead:
    """Tests for reading LDT files."""

    def test_read_from_path(self, sample_path):
        """Read LDT from file path."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        assert ldt.header is not None
        assert ldt.photometry is not None

    def test_read_from_file_handle(self, sample_path):
        """Read LDT from file handle."""
        with open(sample_path / "sample_ldt.ldt", "r") as f:
            ldt = LDTFile.read(f)
        assert ldt.photometry is not None

    def test_read_axial(self, sample_path):
        """Read LDT with axial symmetry (Isym=1)."""
        ldt = LDTFile.read(sample_path / "sample_ldt_axial.ldt")
        assert ldt.header.symmetry == 1
        assert ldt.photometry.symmetry == LampSymmetry.AXIAL

    def test_header_attributes(self, sample_path):
        """Verify header attributes are populated."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        assert ldt.header.manufacturer == "Test Manufacturer"
        assert ldt.header.luminaire_type == 1
        assert ldt.header.symmetry == 2
        assert ldt.header.mc == 7
        assert ldt.header.ng == 7
        assert ldt.header.luminaire_name == "Test Luminaire"

    def test_lamp_data(self, sample_path):
        """Verify lamp data is parsed correctly."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        assert ldt.header.num_lamp_sets == 1
        assert len(ldt.header.lamps) == 1
        assert ldt.header.lamps[0].num_lamps == 1
        assert ldt.header.lamps[0].lamp_type == "LED Module"
        assert ldt.header.lamps[0].total_flux == 3000.0
        assert ldt.header.total_flux == 3000.0

    def test_photometry_values(self, sample_path):
        """Verify photometry data is parsed."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        assert len(ldt.photometry.thetas) == 7
        assert len(ldt.photometry.phis) == 7
        assert ldt.photometry.values.shape == (7, 7)

    def test_candela_conversion(self, sample_path):
        """Values should be converted from cd/klm to candela."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        # First value is 250 cd/klm with 3000 lm total flux
        # candela = (250 * 3000) / 1000 = 750
        assert np.isclose(ldt.photometry.values[0, 0], 750.0)


class TestLDTFileWrite:
    """Tests for writing LDT files."""

    def test_write_to_file(self, sample_path, tmp_path):
        """Write LDT to file."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        outpath = tmp_path / "written.ldt"
        ldt.write(outpath)
        assert outpath.exists()

    def test_write_returns_bytes(self, sample_path):
        """Write with no filename returns bytes."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        result = ldt.write(filename=None)
        assert isinstance(result, bytes)

    def test_round_trip(self, sample_path, tmp_path):
        """Round-trip preserves data."""
        original = LDTFile.read(sample_path / "sample_ldt.ldt")
        outpath = tmp_path / "roundtrip.ldt"
        original.write(outpath)
        reread = LDTFile.read(outpath)

        # Check angles are preserved
        np.testing.assert_array_almost_equal(
            original.photometry.thetas,
            reread.photometry.thetas,
            decimal=1
        )
        np.testing.assert_array_almost_equal(
            original.photometry.phis,
            reread.photometry.phis,
            decimal=1
        )

    def test_write_full(self, sample_path, tmp_path):
        """Write with which='full' expands angles."""
        ldt = LDTFile.read(sample_path / "sample_ldt_axial.ldt")
        outpath = tmp_path / "full.ldt"
        ldt.write(outpath, which="full")
        assert outpath.exists()


class TestLDTFileScaling:
    """Tests for LDTFile scaling methods."""

    def test_scale_to_max(self, sample_path):
        """scale_to_max sets maximum value."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        ldt.scale_to_max(100)
        assert np.isclose(ldt.photometry.max(), 100)

    def test_scale(self, sample_path):
        """scale multiplies values."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        original_max = ldt.photometry.max()
        ldt.scale(2.0)
        np.testing.assert_allclose(ldt.photometry.max(), original_max * 2)

    def test_scale_to_total(self, sample_path):
        """scale_to_total sets total optical power."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        ldt.scale_to_total(1000)
        assert np.isclose(ldt.total(), 1000, rtol=0.01)


class TestLDTFileEquality:
    """Tests for LDTFile equality."""

    def test_equal_files(self, sample_path):
        """Same file loads equal."""
        ldt1 = LDTFile.read(sample_path / "sample_ldt.ldt")
        ldt2 = LDTFile.read(sample_path / "sample_ldt.ldt")
        assert ldt1 == ldt2

    def test_different_files(self, sample_path):
        """Different files not equal."""
        ldt1 = LDTFile.read(sample_path / "sample_ldt.ldt")
        ldt2 = LDTFile.read(sample_path / "sample_ldt_axial.ldt")
        assert ldt1 != ldt2

    def test_deepcopy(self, sample_path):
        """Deepcopy creates equal but independent object."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        copied = copy.deepcopy(ldt)
        assert ldt == copied
        copied.scale(2.0)
        assert ldt != copied


class TestLDTFileMethods:
    """Tests for various LDTFile methods."""

    def test_max(self, sample_path):
        """max returns maximum intensity."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        max_val = ldt.max()
        assert max_val == ldt.photometry.max()
        assert max_val > 0

    def test_total(self, sample_path):
        """total returns total optical power."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        total = ldt.total()
        assert total > 0

    def test_center(self, sample_path):
        """center returns center intensity."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        center_val = ldt.center()
        assert center_val == ldt.photometry.center()

    def test_expanded(self, sample_path):
        """expanded returns expanded photometry."""
        ldt = LDTFile.read(sample_path / "sample_ldt_axial.ldt")
        expanded = ldt.expanded()
        assert expanded is not None
        assert len(expanded.phis) >= len(ldt.photometry.phis)

    def test_lamp_area(self, sample_path):
        """lamp_area returns luminous opening area."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        area_m = ldt.lamp_area("meters")
        area_mm = ldt.lamp_area("mm")
        # Area in mm^2 should be 1e6 times area in m^2
        np.testing.assert_allclose(area_mm, area_m * 1e6, rtol=0.01)


class TestLDTFileFromPhotometry:
    """Tests for creating LDTFile from Photometry."""

    def test_from_photometry(self):
        """Can create LDTFile from standalone Photometry."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        ldt = LDTFile.from_photometry(phot)
        assert ldt.photometry is phot
        assert ldt.header is not None

    def test_from_photometry_header_defaults(self):
        """Header should have sensible defaults."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        ldt = LDTFile.from_photometry(phot)
        assert ldt.header.manufacturer == "PhotomPy"
        assert ldt.header.num_lamp_sets == 1
        assert len(ldt.header.lamps) == 1

    def test_from_photometry_write(self, tmp_path):
        """LDTFile from Photometry should be writable."""
        phot = Photometry(
            thetas=np.array([0, 45, 90]),
            phis=np.array([0, 180]),
            values=np.array([[100, 70, 20], [100, 70, 20]], dtype=float),
            photometric_type=PhotometricType.C
        )
        ldt = LDTFile.from_photometry(phot)
        outfile = tmp_path / "from_phot.ldt"
        ldt.write(outfile)
        assert outfile.exists()


class TestLDTFileAttributePassthrough:
    """Test attribute passthrough to header/photometry."""

    def test_passthrough_to_photometry(self, sample_path):
        """Should pass through photometry attributes."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        assert ldt.thetas is ldt.photometry.thetas
        assert ldt.phis is ldt.photometry.phis

    def test_passthrough_to_header(self, sample_path):
        """Should pass through header attributes."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        assert ldt.manufacturer == ldt.header.manufacturer
        assert ldt.luminaire_name == ldt.header.luminaire_name

    def test_unknown_attribute_raises(self, sample_path):
        """Unknown attributes should raise AttributeError."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        with pytest.raises(AttributeError):
            _ = ldt.nonexistent_attribute


class TestLDTFileCheckFilename:
    """Tests for LDTFile._check_filename method."""

    def test_valid_ldt_extension(self, tmp_path):
        """Should not raise for .ldt extension."""
        path = tmp_path / "test.ldt"
        LDTFile._check_filename(path)

    def test_invalid_extension_strict(self, tmp_path):
        """Should raise for non-.ldt extension with strict=True."""
        path = tmp_path / "test.txt"
        with pytest.raises(LDTPathError, match="Unexpected extension"):
            LDTFile._check_filename(path, strict=True)

    def test_invalid_extension_not_strict(self, tmp_path):
        """Should warn for non-.ldt extension with strict=False."""
        path = tmp_path / "test.txt"
        with pytest.warns(UserWarning, match="Unexpected extension"):
            LDTFile._check_filename(path, strict=False)


class TestLDTHeader:
    """Tests for LDTHeader class."""

    def test_lamp_symmetry_mapping(self):
        """Test LDT Isym to LampSymmetry mapping."""
        header = LDTHeader(
            manufacturer="Test",
            luminaire_type=1,
            symmetry=0,
            mc=1,
            dc=0,
            ng=1,
            dg=0,
            report_number="",
            luminaire_name="",
            luminaire_number="",
            filename="",
            date_user="",
            length=0,
            width=0,
            height=0,
            luminous_length=0,
            luminous_width=0,
            luminous_height_c0=0,
            luminous_height_c90=0,
            luminous_height_c180=0,
            luminous_height_c270=0,
            dff=0,
            lorl=0,
            conversion_factor=1,
            tilt=0,
            num_lamp_sets=0,
            lamps=(),
        )

        # Test each Isym value
        assert header.update(symmetry=0).lamp_symmetry == LampSymmetry.NONE
        assert header.update(symmetry=1).lamp_symmetry == LampSymmetry.AXIAL
        assert header.update(symmetry=2).lamp_symmetry == LampSymmetry.HALF
        assert header.update(symmetry=3).lamp_symmetry == LampSymmetry.HALF
        assert header.update(symmetry=4).lamp_symmetry == LampSymmetry.QUAD

    def test_total_flux(self):
        """Test total_flux sums all lamp sets."""
        lamp1 = LDTLampSet(num_lamps=2, lamp_type="A", total_flux=1000)
        lamp2 = LDTLampSet(num_lamps=1, lamp_type="B", total_flux=500)
        header = LDTHeader(
            manufacturer="Test",
            luminaire_type=1,
            symmetry=0,
            mc=1,
            dc=0,
            ng=1,
            dg=0,
            report_number="",
            luminaire_name="",
            luminaire_number="",
            filename="",
            date_user="",
            length=0,
            width=0,
            height=0,
            luminous_length=100,
            luminous_width=50,
            luminous_height_c0=0,
            luminous_height_c90=0,
            luminous_height_c180=0,
            luminous_height_c270=0,
            dff=0,
            lorl=0,
            conversion_factor=1,
            tilt=0,
            num_lamp_sets=2,
            lamps=(lamp1, lamp2),
        )
        assert header.total_flux == 1500

    def test_luminous_opening(self):
        """Test luminous_opening property."""
        header = LDTHeader(
            manufacturer="Test",
            luminaire_type=1,
            symmetry=0,
            mc=1,
            dc=0,
            ng=1,
            dg=0,
            report_number="",
            luminaire_name="",
            luminaire_number="",
            filename="",
            date_user="",
            length=500,
            width=300,
            height=200,
            luminous_length=400,
            luminous_width=250,
            luminous_height_c0=50,
            luminous_height_c90=0,
            luminous_height_c180=0,
            luminous_height_c270=0,
            dff=0,
            lorl=0,
            conversion_factor=1,
            tilt=0,
            num_lamp_sets=0,
            lamps=(),
        )
        opening = header.luminous_opening
        # Check dimensions are converted from mm to m
        assert np.isclose(opening.width, 0.250)  # 250 mm
        assert np.isclose(opening.length, 0.400)  # 400 mm
        assert np.isclose(opening.height, 0.050)  # 50 mm


class TestLDTReadHelpers:
    """Tests for LDT read helper functions."""

    def test_candela_conversion(self):
        """Test cd/klm to candela conversion."""
        from photompy.ldt._read import convert_ldt_to_candela

        values = np.array([[100, 200], [150, 250]])
        total_flux = 2000  # lumens

        # candela = (cd/klm * flux) / 1000
        expected = values * total_flux / 1000
        result = convert_ldt_to_candela(values, total_flux)
        np.testing.assert_array_almost_equal(result, expected)

    def test_candela_to_ldt_conversion(self):
        """Test candela to cd/klm conversion."""
        from photompy.ldt._read import convert_candela_to_ldt

        candela = np.array([[200, 400], [300, 500]])
        total_flux = 2000

        # cd/klm = (candela * 1000) / flux
        expected = candela * 1000 / total_flux
        result = convert_candela_to_ldt(candela, total_flux)
        np.testing.assert_array_almost_equal(result, expected)


class TestLDTPlot:
    """Tests for LDTFile.plot method."""

    def test_plot_invalid_type_raises(self, sample_path):
        """plot with invalid type should raise ValueError."""
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        with pytest.raises(ValueError, match="Unrecognized plot type"):
            ldt.plot(plot_type="invalid")

    @pytest.mark.skip(reason="Slow due to matplotlib startup")
    def test_plot_polar(self, sample_path):
        """plot with polar type should work."""
        import matplotlib.pyplot as plt
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        ldt.plot(plot_type="polar")
        plt.close('all')

    @pytest.mark.skip(reason="Slow due to matplotlib startup")
    def test_plot_cartesian(self, sample_path):
        """plot with cartesian type should work."""
        import matplotlib.pyplot as plt
        ldt = LDTFile.read(sample_path / "sample_ldt.ldt")
        ldt.plot(plot_type="cartesian")
        plt.close('all')
