"""Tests for File Generation Type support (LM-63-2019 Section 5.13)."""
import pytest
from pathlib import Path

from photompy import IESFile, FileGeneration


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "data"


class TestFileGeneration:
    """Tests for FileGeneration dataclass."""

    def test_default_is_undefined(self):
        """Default FileGeneration should be undefined (all False)."""
        fg = FileGeneration()
        assert fg.is_undefined
        assert not fg.accredited
        assert not fg.simulated
        assert not fg.interpolated
        assert not fg.scaled

    def test_from_float_undefined(self):
        """1.00001 should parse as undefined."""
        fg = FileGeneration.from_float(1.00001)
        assert fg.is_undefined

    def test_from_float_accredited(self):
        """1.10000 should parse as accredited lab."""
        fg = FileGeneration.from_float(1.10000)
        assert fg.accredited
        assert not fg.simulated
        assert not fg.interpolated
        assert not fg.scaled

    def test_from_float_simulated(self):
        """1.01000 should parse as simulated."""
        fg = FileGeneration.from_float(1.01000)
        assert not fg.accredited
        assert fg.simulated
        assert not fg.interpolated
        assert not fg.scaled

    def test_from_float_interpolated(self):
        """1.00010 should parse as interpolated."""
        fg = FileGeneration.from_float(1.00010)
        assert not fg.accredited
        assert not fg.simulated
        assert fg.interpolated
        assert not fg.scaled

    def test_from_float_scaled(self):
        """1.00001 would be undefined, but 1.00100 is 'reserved' position."""
        # Note: 1.00001 is the undefined marker
        # Let's test 1.00011 (interpolated and scaled)
        fg = FileGeneration.from_float(1.00011)
        assert not fg.accredited
        assert not fg.simulated
        assert fg.interpolated
        assert fg.scaled

    def test_from_float_combined(self):
        """1.10011 should parse as accredited, interpolated, and scaled."""
        fg = FileGeneration.from_float(1.10011)
        assert fg.accredited
        assert not fg.simulated
        assert fg.interpolated
        assert fg.scaled

    def test_to_float_undefined(self):
        """Undefined should convert to 1.00000."""
        fg = FileGeneration()
        assert fg.to_float() == 1.00000

    def test_to_float_accredited(self):
        """Accredited should convert to 1.10000."""
        fg = FileGeneration(accredited=True)
        assert fg.to_float() == 1.10000

    def test_to_float_simulated(self):
        """Simulated should convert to 1.01000."""
        fg = FileGeneration(simulated=True)
        assert fg.to_float() == 1.01000

    def test_to_float_interpolated_scaled(self):
        """Interpolated and scaled should convert to 1.00011."""
        fg = FileGeneration(interpolated=True, scaled=True)
        assert fg.to_float() == 1.00011

    def test_round_trip(self):
        """from_float -> to_float should preserve value."""
        original_values = [1.00000, 1.10000, 1.01000, 1.00010, 1.00001,
                          1.10011, 1.01011, 1.11011]
        for val in original_values:
            fg = FileGeneration.from_float(val)
            # Note: 1.00001 (undefined) becomes 1.00000 on round-trip
            if val == 1.00001:
                assert fg.to_float() == 1.00000
            else:
                assert fg.to_float() == val

    def test_str_undefined(self):
        fg = FileGeneration()
        assert "undefined" in str(fg)

    def test_str_flags(self):
        fg = FileGeneration(accredited=True, interpolated=True)
        s = str(fg)
        assert "accredited" in s
        assert "interpolated" in s
        assert "simulated" not in s


class TestFileGenerationRead:
    """Tests for reading file_generation_type from IES files."""

    def test_read_simulated(self, sample_path):
        """Read file with simulated flag."""
        ies = IESFile.read(sample_path / "filegen_simulated.ies")
        fg = ies.header.file_generation_type
        assert fg.simulated
        assert not fg.accredited

    def test_read_accredited(self, sample_path):
        """Read file with accredited flag."""
        ies = IESFile.read(sample_path / "filegen_accredited.ies")
        fg = ies.header.file_generation_type
        assert fg.accredited
        assert not fg.simulated

    def test_read_scaled_interpolated(self, sample_path):
        """Read file with scaled and interpolated flags."""
        ies = IESFile.read(sample_path / "filegen_scaled_interpolated.ies")
        fg = ies.header.file_generation_type
        assert fg.interpolated
        assert fg.scaled
        assert not fg.accredited
        assert not fg.simulated


class TestFileGenerationVersion:
    """Tests for version-specific file_generation_type behavior."""

    def test_v2019_has_filegen(self, sample_path):
        """LM-63-2019 files should have file_generation_type."""
        ies = IESFile.read(sample_path / "filegen_accredited.ies")
        assert ies.header.version.supports_filegen
        fg = ies.header.file_generation_type
        assert isinstance(fg, FileGeneration)

    def test_v2002_raises(self, sample_path):
        """LM-63-2002 files should raise AttributeError for file_generation_type."""
        ies = IESFile.read(sample_path / "sample_A.ies")
        assert not ies.header.version.supports_filegen
        with pytest.raises(AttributeError):
            _ = ies.header.file_generation_type

    def test_v2002_has_future_use(self, sample_path):
        """LM-63-2002 files should have future_use property."""
        ies = IESFile.read(sample_path / "sample_A.ies")
        # future_use should work for all versions
        _ = ies.header.future_use


class TestFileGenerationRoundTrip:
    """Round-trip tests for file_generation_type."""

    def test_round_trip_preserves_filegen(self, sample_path, tmp_path):
        """file_generation_type should be preserved on write."""
        original = IESFile.read(sample_path / "filegen_accredited.ies")
        outfile = tmp_path / "roundtrip.ies"
        original.write(outfile)

        reread = IESFile.read(outfile)
        assert reread.header.file_generation_type.accredited
        assert reread.header._v11 == original.header._v11

    def test_round_trip_simulated(self, sample_path, tmp_path):
        """Simulated flag should be preserved."""
        original = IESFile.read(sample_path / "filegen_simulated.ies")
        outfile = tmp_path / "roundtrip.ies"
        original.write(outfile)

        reread = IESFile.read(outfile)
        assert reread.header.file_generation_type.simulated
