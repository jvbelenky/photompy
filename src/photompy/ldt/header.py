"""
LDT (EULUMDAT) Header dataclass.

This module contains the LDTHeader dataclass that stores all metadata
from an EULUMDAT photometric file. The format is the European equivalent
of IES files.

EULUMDAT Format Reference:
- Lines 1-26+ contain fixed positional header data
- Lines 27+ contain angle and intensity data
"""

from dataclasses import dataclass, replace, asdict
from typing import Union
from ..photometry import LampSymmetry


@dataclass(frozen=True, slots=True)
class LDTLampSet:
    """
    Per-lamp-set data from LDT header.

    Each lamp set contains 6 values:
    - num_lamps: Number of lamps in this set (negative for absolute photometry)
    - lamp_type: Description of lamp type
    - total_flux: Total luminous flux in lumens for this set
    - color: Color appearance / color temperature
    - cri: Color rendering index (group)
    - wattage: Wattage including ballast
    """

    num_lamps: int
    lamp_type: str
    total_flux: float
    color: str = ""
    cri: str = ""
    wattage: float = 0.0


@dataclass(frozen=True, slots=True)
class LDTHeader:
    """
    LDT (EULUMDAT) header data.

    Stores all metadata from the fixed header lines of an EULUMDAT file.
    Dimensions are stored in millimeters as per the EULUMDAT specification.

    Attributes:
        manufacturer: Company/lab identification (line 1)
        luminaire_type: Ityp - 1=point source with symm. about vert axis,
                       2=linear luminaire, 3=point source with other symm. (line 2)
        symmetry: Isym - 0=no symmetry, 1=axially symmetric, 2=C0-C180 symmetry,
                 3=C90-C270 symmetry, 4=C0-C180 and C90-C270 symmetry (line 3)
        mc: Number of C-planes between C0 and C360 (line 4)
        dc: Distance between C-planes in degrees (line 5)
        ng: Number of luminous intensities per C-plane (line 6)
        dg: Distance between gamma angles in degrees (line 7)
        report_number: Measurement report number (line 8)
        luminaire_name: Luminaire name/description (line 9)
        luminaire_number: Luminaire number/catalog number (line 10)
        filename: Original filename (line 11)
        date_user: Date and user info (line 12)
        length: Luminaire length in mm (line 13)
        width: Luminaire width in mm (line 14)
        height: Luminaire height in mm (line 15)
        luminous_length: Luminous area length in mm (line 16)
        luminous_width: Luminous area width in mm (line 17)
        luminous_height_c0: Luminous area height at C0 in mm (line 18)
        luminous_height_c90: Luminous area height at C90 in mm (line 19)
        luminous_height_c180: Luminous area height at C180 in mm (line 20)
        luminous_height_c270: Luminous area height at C270 in mm (line 21)
        dff: Downward flux fraction as percentage (line 22)
        lorl: Light output ratio of luminaire as percentage (line 23)
        conversion_factor: Conversion factor for luminous intensities (line 24)
        tilt: Tilt of luminaire during measurement in degrees (line 25)
        num_lamp_sets: Number of standard lamp sets (line 26)
        lamps: List of LDTLampSet objects (lines 26a-26c per set)
    """

    # Identification (lines 1-12)
    manufacturer: str
    luminaire_type: int  # Ityp: 1, 2, or 3
    symmetry: int  # Isym: 0-4
    mc: int  # number of C-planes
    dc: float  # C-plane spacing (degrees)
    ng: int  # intensities per C-plane
    dg: float  # G-angle spacing (degrees)
    report_number: str
    luminaire_name: str
    luminaire_number: str
    filename: str
    date_user: str

    # Dimensions in mm (lines 13-21)
    length: float
    width: float
    height: float
    luminous_length: float
    luminous_width: float
    luminous_height_c0: float
    luminous_height_c90: float
    luminous_height_c180: float
    luminous_height_c270: float

    # Photometric data (lines 22-25)
    dff: float  # downward flux fraction %
    lorl: float  # light output ratio %
    conversion_factor: float
    tilt: float  # degrees

    # Lamp data (line 26+)
    num_lamp_sets: int
    lamps: tuple[LDTLampSet, ...]  # Immutable tuple for frozen dataclass

    @property
    def total_flux(self) -> float:
        """Total luminous flux from all lamp sets in lumens."""
        return sum(lamp.total_flux for lamp in self.lamps)

    @property
    def lamp_symmetry(self) -> LampSymmetry:
        """
        Convert LDT Isym to LampSymmetry enum.

        Mapping:
        - 0: No symmetry → NONE
        - 1: Axially symmetric → AXIAL
        - 2: C0-C180 symmetry → HALF
        - 3: C90-C270 symmetry → HALF
        - 4: Quadrant symmetry → QUAD
        """
        mapping = {
            0: LampSymmetry.NONE,
            1: LampSymmetry.AXIAL,
            2: LampSymmetry.HALF,
            3: LampSymmetry.HALF,
            4: LampSymmetry.QUAD,
        }
        return mapping.get(self.symmetry, LampSymmetry.UNKNOWN)

    @property
    def luminous_opening(self):
        """
        Get the luminous opening geometry.

        Returns:
            LuminousOpening object with dimensions converted from mm to meters
        """
        from ..geometry import LuminousOpening

        # Convert mm to meters
        factor = 0.001

        # For LDT files, we use luminous_width as width, luminous_length as length
        # LDT doesn't encode shape via sign like IES, so we use positive values
        return LuminousOpening(
            width=self.luminous_width * factor,
            length=self.luminous_length * factor,
            height=self.luminous_height_c0 * factor,
        )

    @classmethod
    def from_lines(
        cls,
        lines: list[str],
        strict: bool = True,
    ) -> tuple["LDTHeader", int]:
        """
        Parse LDT header from file lines.

        Args:
            lines: List of stripped lines from LDT file
            strict: If True, raise errors on malformed data

        Returns:
            Tuple of (LDTHeader instance, data_start_index)
        """
        from ..exceptions import LDTHeaderError

        def get_line(idx: int, convert=str) -> Union[str, int, float]:
            """Get line at index with type conversion."""
            try:
                val = lines[idx].strip()
                return convert(val) if convert != str else val
            except (IndexError, ValueError) as e:
                if strict:
                    raise LDTHeaderError(f"Error parsing line {idx + 1}: {e}") from None
                return convert() if convert != str else ""

        def get_float(idx: int) -> float:
            return get_line(idx, float)

        def get_int(idx: int) -> int:
            return get_line(idx, int)

        # Parse fixed header lines (0-indexed, but spec uses 1-indexed)
        manufacturer = get_line(0)
        luminaire_type = get_int(1)
        symmetry = get_int(2)
        mc = get_int(3)
        dc = get_float(4)
        ng = get_int(5)
        dg = get_float(6)
        report_number = get_line(7)
        luminaire_name = get_line(8)
        luminaire_number = get_line(9)
        filename = get_line(10)
        date_user = get_line(11)

        # Dimensions
        length = get_float(12)
        width = get_float(13)
        height = get_float(14)
        luminous_length = get_float(15)
        luminous_width = get_float(16)
        luminous_height_c0 = get_float(17)
        luminous_height_c90 = get_float(18)
        luminous_height_c180 = get_float(19)
        luminous_height_c270 = get_float(20)

        # Photometric info
        dff = get_float(21)
        lorl = get_float(22)
        conversion_factor = get_float(23)
        tilt = get_float(24)

        # Lamp sets
        num_lamp_sets = get_int(25)

        lamps = []
        line_idx = 26
        lines_per_lamp_set = 6  # Full EULUMDAT format: num, type, flux, color, cri, wattage
        has_direct_ratios = True

        # Detect format by checking if line after lamp data looks like direct ratios
        # Direct ratios are 10 float values between 0 and 1
        expected_end_idx = line_idx + (6 * num_lamp_sets)
        if expected_end_idx + 10 <= len(lines):
            try:
                # Check if the 10 lines after lamp sets look like direct ratios
                first_ratio = float(lines[expected_end_idx].strip())
                if not (0 <= first_ratio <= 1.5):  # Direct ratios are typically 0.5-1.0
                    # Doesn't look like direct ratios, try simpler format
                    lines_per_lamp_set = 3
                    has_direct_ratios = False
            except (ValueError, IndexError):
                # Try simpler format
                lines_per_lamp_set = 3
                has_direct_ratios = False
        else:
            # Not enough lines for full format, try simpler
            lines_per_lamp_set = 3
            has_direct_ratios = False

        for _ in range(num_lamp_sets):
            try:
                num_lamps = int(lines[line_idx].strip())
                lamp_type = lines[line_idx + 1].strip()
                total_flux = float(lines[line_idx + 2].strip())
                if lines_per_lamp_set == 6:
                    color = lines[line_idx + 3].strip() if len(lines) > line_idx + 3 else ""
                    cri = lines[line_idx + 4].strip() if len(lines) > line_idx + 4 else ""
                    wattage = float(lines[line_idx + 5].strip()) if len(lines) > line_idx + 5 else 0.0
                else:
                    color, cri, wattage = "", "", 0.0
                lamps.append(LDTLampSet(num_lamps, lamp_type, total_flux, color, cri, wattage))
                line_idx += lines_per_lamp_set
            except (IndexError, ValueError) as e:
                if strict:
                    raise LDTHeaderError(f"Error parsing lamp set: {e}") from None
                break

        # Skip 10 direct ratio lines if present (Dk values for room indices 0.6 to 5.0)
        if has_direct_ratios:
            line_idx += 10

        header = cls(
            manufacturer=manufacturer,
            luminaire_type=luminaire_type,
            symmetry=symmetry,
            mc=mc,
            dc=dc,
            ng=ng,
            dg=dg,
            report_number=report_number,
            luminaire_name=luminaire_name,
            luminaire_number=luminaire_number,
            filename=filename,
            date_user=date_user,
            length=length,
            width=width,
            height=height,
            luminous_length=luminous_length,
            luminous_width=luminous_width,
            luminous_height_c0=luminous_height_c0,
            luminous_height_c90=luminous_height_c90,
            luminous_height_c180=luminous_height_c180,
            luminous_height_c270=luminous_height_c270,
            dff=dff,
            lorl=lorl,
            conversion_factor=conversion_factor,
            tilt=tilt,
            num_lamp_sets=num_lamp_sets,
            lamps=tuple(lamps),
        )
        return header, line_idx

    @classmethod
    def from_photometry(
        cls,
        phot,
        *,
        # Required parameters (no defaults)
        manufacturer: str,
        luminaire_name: str,
        # Optional parameters with sensible defaults
        luminaire_number: str = "",
        luminaire_type: int = 1,
        report_number: str = "",
        date_user: str = "",
        # Dimensions in mm
        length: float = 0.0,
        width: float = 0.0,
        height: float = 0.0,
        luminous_length: float = 0.0,
        luminous_width: float = 0.0,
        luminous_height: float = 0.0,
        # Photometric characteristics
        dff: float = None,
        lorl: float = 100.0,
        tilt: float = 0.0,
        # Lamp data
        num_lamps: int = 1,
        lamp_type: str = "LED",
        total_flux: float = None,
    ) -> "LDTHeader":
        """
        Create an LDT header from photometry data with metadata.

        The EULUMDAT format requires certain fields. The following are required
        by this method (no defaults):
        - manufacturer: Company/manufacturer name (line 1)
        - luminaire_name: Luminaire description (line 9)

        Args:
            phot: Photometry object with angular intensity distribution
            manufacturer: Company/manufacturer name (required)
            luminaire_name: Luminaire description (required)
            luminaire_number: Catalog number (default "")
            luminaire_type: 1=point source, 2=linear, 3=other (default 1)
            report_number: Test report number (default "")
            date_user: Date and user info (default "")
            length: Luminaire length in mm (default 0.0)
            width: Luminaire width in mm (default 0.0)
            height: Luminaire height in mm (default 0.0)
            luminous_length: Luminous area length in mm (default 0.0)
            luminous_width: Luminous area width in mm (default 0.0)
            luminous_height: Luminous area height in mm, sets all C-planes (default 0.0)
            dff: Downward flux fraction % (calculated from photometry if None)
            lorl: Light output ratio % (default 100.0)
            tilt: Tilt during measurement in degrees (default 0.0)
            num_lamps: Number of lamps (default 1)
            lamp_type: Lamp type description (default "LED")
            total_flux: Total luminous flux in lumens (calculated from photometry if None)

        Returns:
            LDTHeader with populated fields

        Raises:
            TypeError: If any required parameter is missing
        """
        # Infer symmetry from photometry
        symmetry_map = {
            LampSymmetry.NONE: 0,
            LampSymmetry.AXIAL: 1,
            LampSymmetry.HALF: 2,
            LampSymmetry.QUAD: 4,
            LampSymmetry.UNKNOWN: 0,
        }
        isym = symmetry_map.get(phot.symmetry, 0)

        # Calculate total flux from photometry if not provided
        if total_flux is None:
            total_flux = phot.total_optical_power()

        # Calculate DFF (downward flux fraction) if not provided
        if dff is None:
            # For Type C, downward is theta 0-90, upward is 90-180
            # This is a simplification - proper calculation requires integration
            dff = 100.0  # Default to 100% downward for now

        # Create lamp set
        lamp_set = LDTLampSet(
            num_lamps=num_lamps,
            lamp_type=lamp_type,
            total_flux=total_flux,
            color="",
            cri="",
            wattage=0.0,
        )

        return cls(
            manufacturer=manufacturer,
            luminaire_type=luminaire_type,
            symmetry=isym,
            mc=len(phot.phis),
            dc=phot.phis[1] - phot.phis[0] if len(phot.phis) > 1 else 0,
            ng=len(phot.thetas),
            dg=phot.thetas[1] - phot.thetas[0] if len(phot.thetas) > 1 else 0,
            report_number=report_number,
            luminaire_name=luminaire_name,
            luminaire_number=luminaire_number,
            filename="",
            date_user=date_user,
            length=length,
            width=width,
            height=height,
            luminous_length=luminous_length,
            luminous_width=luminous_width,
            luminous_height_c0=luminous_height,
            luminous_height_c90=luminous_height,
            luminous_height_c180=luminous_height,
            luminous_height_c270=luminous_height,
            dff=dff,
            lorl=lorl,
            conversion_factor=1.0,
            tilt=tilt,
            num_lamp_sets=1,
            lamps=(lamp_set,),
        )

    def to_dict(self) -> dict:
        """Return header as dictionary."""
        return asdict(self)

    def update(self, **changes) -> "LDTHeader":
        """Return a new header with updated fields."""
        return replace(self, **changes)

    def header_line_count(self) -> int:
        """Return the number of header lines (including lamp sets and direct ratios)."""
        # 26 base header lines
        # + 6 lines per lamp set (num, type, flux, color, cri, wattage)
        # + 10 direct ratio lines (Dk for room indices 0.6 to 5.0)
        return 26 + (6 * self.num_lamp_sets) + 10
