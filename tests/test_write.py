"""Tests for write.py module."""
import pytest
import numpy as np
import warnings
from photompy.write import process_row, write_ies_data
from photompy.read import read_ies_data


class TestProcessRow:
    def test_short_row(self):
        row = [1.0, 2.0, 3.0]
        result = process_row(row)
        assert "1.0" in result
        assert "2.0" in result
        assert "3.0" in result
        assert result.endswith("\n")

    def test_line_wrapping(self):
        row = [float(i) for i in range(50)]  # Long row
        result = process_row(row)
        lines = result.strip().split("\n")
        # Should wrap to multiple lines
        assert len(lines) > 1

    def test_precision(self):
        row = [1.123456789]
        result = process_row(row, sigfigs=3)
        assert "1.123" in result

    def test_single_element(self):
        row = [100.0]
        result = process_row(row)
        assert "100.0" in result
        assert result.endswith("\n")


class TestWriteIesData:
    def test_round_trip(self, sample_path, tmp_path):
        """Read -> Write -> Read should preserve data."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies")

        outfile = tmp_path / "output.ies"
        write_ies_data(lampdict, filename=outfile)

        assert outfile.exists()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            reread = read_ies_data(outfile)

        np.testing.assert_array_almost_equal(
            lampdict["original_vals"]["values"],
            reread["original_vals"]["values"],
            decimal=2
        )

    def test_write_to_bytes(self, sample_path):
        """Write without filename returns bytes."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies")

        result = write_ies_data(lampdict, filename=None)
        assert isinstance(result, bytes)
        assert b"IESNA" in result or b"IES" in result

    def test_header_preserved(self, sample_path, tmp_path):
        """Header values should be preserved on write."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies")

        outfile = tmp_path / "output.ies"
        write_ies_data(lampdict, filename=outfile)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            reread = read_ies_data(outfile)

        assert lampdict["num_lamps"] == reread["num_lamps"]
        assert lampdict["photometric_type"] == reread["photometric_type"]

    def test_angles_preserved(self, sample_path, tmp_path):
        """Angle arrays should be preserved on write."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies")

        outfile = tmp_path / "output.ies"
        write_ies_data(lampdict, filename=outfile)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            reread = read_ies_data(outfile)

        np.testing.assert_array_almost_equal(
            lampdict["original_vals"]["thetas"],
            reread["original_vals"]["thetas"],
            decimal=2
        )
        np.testing.assert_array_almost_equal(
            lampdict["original_vals"]["phis"],
            reread["original_vals"]["phis"],
            decimal=2
        )

    def test_write_full_vals(self, sample_path, tmp_path):
        """Can write using full_vals key."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lampdict = read_ies_data(sample_path / "sample_A.ies")

        outfile = tmp_path / "output.ies"
        write_ies_data(lampdict, filename=outfile, valkey="full_vals")

        assert outfile.exists()
        # Multiplier should be set to 1 when writing full_vals
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            reread = read_ies_data(outfile)
        assert reread["multiplier"] == 1.0
