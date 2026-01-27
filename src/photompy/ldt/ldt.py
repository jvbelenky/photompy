"""
LDT (EULUMDAT) file handling.

This module provides the LDTFile class for reading and writing
EULUMDAT photometric data files, the European equivalent of IES files.
"""

from dataclasses import dataclass, asdict
import pathlib
import warnings
import copy
from ..photometry import Photometry, PhotometricType
from .._read import load_bytes
from ._read import (
    parse_ldt_lines,
    parse_ldt_header,
    parse_ldt_angles,
    complete_ldt_symmetry,
    convert_ldt_to_candela,
)
from ._write import (
    format_ldt_header,
    format_ldt_angles,
    format_ldt_values,
    prepare_photometry_for_ldt,
)
from ..exceptions import LDTPathError
from .header import LDTHeader


@dataclass
class LDTFile:
    """
    EULUMDAT (LDT) photometric data file.

    Provides an interface similar to IESFile for reading, writing, and
    manipulating LDT photometric data.

    Attributes:
        source: Original source (path, bytes, or string)
        header: LDTHeader with all metadata
        photometry: Photometry object with intensity data
    """

    source: str | pathlib.Path | bytes
    header: LDTHeader
    photometry: Photometry

    def __getattr__(self, name):
        """Passthrough to header/photometry for convenience."""
        if hasattr(self.photometry, name):
            return getattr(self.photometry, name)
        if hasattr(self.header, name):
            return getattr(self.header, name)
        raise AttributeError(name)

    def __deepcopy__(self, memo):
        """Custom deepcopy to avoid __getattr__ recursion."""
        cls = self.__class__
        new_obj = cls.__new__(cls)
        memo[id(self)] = new_obj

        for k, v in self.__dict__.items():
            if k in ("header", "photometry"):
                setattr(new_obj, k, copy.deepcopy(v, memo))
            else:
                setattr(new_obj, k, v)

        return new_obj

    def __eq__(self, other):
        if not isinstance(other, LDTFile):
            return NotImplemented
        if self.header != other.header:
            return False
        if self.photometry != other.photometry:
            return False
        return True

    def to_dict(self):
        """Return as dictionary."""
        return asdict(self)

    @classmethod
    def read(cls, src, strict: bool = True) -> "LDTFile":
        """
        Parse an LDT file from any source.

        Args:
            src: File path (str or Path), bytes, or file-like object
            strict: If True, raise errors on malformed data

        Returns:
            LDTFile instance
        """
        raw, origin = load_bytes(src)
        if origin is not None:
            cls._check_filename(origin=origin, strict=strict)

        # Decode with fallback for different encodings
        try:
            string = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                string = raw.decode("latin-1")
            except UnicodeDecodeError:
                string = raw.decode("cp1252", errors="replace")

        lines = parse_ldt_lines(string)

        # Parse header
        header, data_start = parse_ldt_header(lines, strict=strict)

        # Parse angles and values
        c_angles, g_angles, values = parse_ldt_angles(
            lines,
            start_idx=data_start,
            mc=header.mc,
            ng=header.ng,
            isym=header.symmetry,
            strict=strict,
        )

        # Complete symmetry and convert to Photometry coordinate system
        phis, thetas, expanded_values = complete_ldt_symmetry(
            c_angles, g_angles, values, header.symmetry
        )

        # Convert cd/klm to absolute candela
        candela_values = convert_ldt_to_candela(expanded_values, header.total_flux)

        # Apply conversion factor if present
        if header.conversion_factor != 0 and header.conversion_factor != 1:
            candela_values = candela_values * header.conversion_factor

        # Create Photometry object
        # LDT files always use Type C photometry (nadir-based)
        phot = Photometry(
            thetas=thetas,
            phis=phis,
            values=candela_values,
            photometric_type=PhotometricType.C,
        )

        return cls(source=src, header=header, photometry=phot)

    @classmethod
    def from_photometry(
        cls,
        phot: Photometry,
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
    ) -> "LDTFile":
        """
        Create an LDTFile from photometry data with metadata.

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
            LDTFile with populated header and photometry

        Raises:
            TypeError: If any required parameter is missing

        Example:
            >>> import numpy as np
            >>> from photompy import Photometry, LDTFile, PhotometricType
            >>>
            >>> thetas = np.linspace(0, 90, 19)
            >>> phis = np.array([0])
            >>> values = np.cos(np.deg2rad(thetas))[None, :] * 1000
            >>> phot = Photometry(thetas, phis, values, PhotometricType.C)
            >>>
            >>> ldt = LDTFile.from_photometry(
            ...     phot,
            ...     manufacturer="Acme Lighting",
            ...     luminaire_name="Downlight DL-100",
            ...     luminous_width=50,
            ...     luminous_length=50,
            ... )
            >>> ldt.write("downlight.ldt")
        """
        header = LDTHeader.from_photometry(
            phot,
            manufacturer=manufacturer,
            luminaire_name=luminaire_name,
            luminaire_number=luminaire_number,
            luminaire_type=luminaire_type,
            report_number=report_number,
            date_user=date_user,
            length=length,
            width=width,
            height=height,
            luminous_length=luminous_length,
            luminous_width=luminous_width,
            luminous_height=luminous_height,
            dff=dff,
            lorl=lorl,
            tilt=tilt,
            num_lamps=num_lamps,
            lamp_type=lamp_type,
            total_flux=total_flux,
        )
        return cls(source=None, header=header, photometry=phot)

    def update(self, **changes) -> "LDTFile":
        """
        Update header fields.

        Args:
            **changes: Header fields to update

        Returns:
            Self for method chaining
        """
        self.header = self.header.update(**changes)
        return self

    def scale_to_max(self, max_val: float) -> "LDTFile":
        """Scale the photometry to a maximum value."""
        self.photometry.scale_to_max(max_val)
        return self

    def scale_to_total(self, total_power: float) -> "LDTFile":
        """Scale the photometry to a total optical power."""
        self.photometry.scale_to_total(total_power)
        return self

    def scale_to_center(self, center_val: float) -> "LDTFile":
        """Scale the photometry to a center value."""
        self.photometry.scale_to_center(center_val)
        return self

    def scale(self, scale_val: float) -> "LDTFile":
        """Scale the photometry by the given value."""
        self.photometry.scale(scale_val)
        return self

    @property
    def luminous_opening(self):
        """Get the luminous opening geometry."""
        return self.header.luminous_opening

    def lamp_area(self, units: str = "meters") -> float:
        """
        Get the luminous opening area.

        Args:
            units: "meters", "m", "feet", "ft", "inches", "in",
                   "cm", "centimeters", "mm", "millimeters"

        Returns:
            Area in the specified units squared
        """
        return self.luminous_opening.area_in(units)

    def write(
        self,
        filename=None,
        which: str = "orig",
        precision: int = 2,
    ):
        """
        Write the photometry to an LDT file.

        Args:
            filename: Output file path (or None to return bytes)
            which: "orig" for original data, "full" for expanded
            precision: Decimal places for numeric values

        Returns:
            None if filename provided, bytes otherwise
        """
        # Prepare data using original photometry (prepare_photometry_for_ldt handles expansion)
        phis, thetas, values, isym = prepare_photometry_for_ldt(self.photometry, which)

        # Update header with current dimensions
        header = self.header.update(
            mc=len(phis),
            ng=len(thetas),
            symmetry=isym,
            dc=phis[1] - phis[0] if len(phis) > 1 else 0,
            dg=thetas[1] - thetas[0] if len(thetas) > 1 else 0,
        )

        # Format output
        ldt_data = format_ldt_header(header)
        ldt_data += format_ldt_angles(phis, thetas, precision=precision)
        ldt_data += format_ldt_values(values, header.total_flux, precision=precision)

        if filename is not None:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(ldt_data)
        else:
            return ldt_data.encode("utf-8")

    def plot(
        self,
        plot_type: str = "polar",
        which: str = "full",
        interp_args: tuple = (181, 361),
        **kwargs,
    ):
        """
        Return a polar or 3D cartesian plot of the photometry.

        Args:
            plot_type: "polar" or "cartesian"
            which: "orig", "full", or "interp"
            interp_args: (num_thetas, num_phis) for interpolation
            **kwargs: Passed to plot function

        Returns:
            matplotlib figure
        """
        photometry = self._get_photometry(which, interp_args)
        if plot_type.lower() == "polar":
            return photometry.plot_polar(**kwargs)
        elif plot_type.lower() == "cartesian":
            return photometry.plot_cartesian(**kwargs)
        else:
            raise ValueError(f"Unrecognized plot type: {plot_type}")

    def _get_photometry(self, which: str, interp_args: tuple = (181, 361)) -> Photometry:
        """Get photometry based on requested mode."""
        if which.lower() == "orig":
            return self.photometry
        elif which.lower() == "full":
            return self.photometry.expanded()
        elif which.lower() == "interp":
            return self.photometry.interpolated(*interp_args)
        raise ValueError(f"Unknown photometry mode: {which}")

    @staticmethod
    def _check_filename(origin: pathlib.Path, strict: bool = True):
        """Validate file extension."""
        if origin.suffix.lower() != ".ldt":
            msg = f"Unexpected extension {origin.suffix!s}. Expected .ldt"
            if strict:
                raise LDTPathError(msg)
            else:
                warnings.warn(msg, stacklevel=3)
