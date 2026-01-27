from dataclasses import dataclass, asdict
import pathlib
import warnings
import copy
from typing import Union
from .photometry import Photometry
from ._read import load_bytes, process_keywords, read_angles
from ._write import process_row
from .exceptions import IESPathError, IESHeaderError  # , IESDecodeError,
from .ies_header import IESHeader, IESVersion, Units, FileGeneration
from .tilt import TiltData


@dataclass
class IESFile:
    source: str | pathlib.Path | bytes
    header: IESHeader
    photometry: Photometry

    # TODO: fix this
    # attribute passthrough to header / photometry -------------
    def __getattr__(self, name):
        # called only if normal attribute lookup fails
        if hasattr(self.photometry, name):
            return getattr(self.photometry, name)
        if hasattr(self.header, name):
            return getattr(self.header, name)
        raise AttributeError(name)

    def __deepcopy__(self, memo):
        """
        Custom deepcopy to avoid the __getattr__ recursion issue.
        We duplicate header and photometry explicitly instead of
        letting copy traverse the whole object graph.
        """
        cls = self.__class__
        new_obj = cls.__new__(cls)
        memo[id(self)] = new_obj

        # shallow-copy simple attributes
        for k, v in self.__dict__.items():
            if k in ("header", "photometry"):
                # these may be big → real deepcopy
                setattr(new_obj, k, copy.deepcopy(v, memo))
            else:
                setattr(new_obj, k, v)

        return new_obj

    def __eq__(self, other):
        if self.header != other.header:
            return False
        if self.photometry != other.photometry:
            return False
        return True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def read(cls, src, strict=True):
        """parse an ies file from any source"""
        raw, origin = load_bytes(src)
        if origin is not None:  # check filename
            cls._check_filename(origin=origin, strict=strict)

        string = raw.decode("utf-8")

        version, header, tilt, numeric, blocks = cls._split_string(string)

        version = IESVersion.from_token(version, strict=strict)

        hdr = IESHeader.from_tokens(
            version=version,
            keywords=process_keywords(header),
            tilt=tilt,
            numeric=numeric,
            strict=strict,
        )

        thetas, phis, values = read_angles(
            blocks, hdr.num_vert_angles, hdr.num_horiz_angles
        )
        phot = Photometry(
            thetas=thetas,
            phis=phis,
            values=values * hdr.multiplier,
            photometric_type=hdr.photometric_type,
        )

        hdr = hdr.update(multiplier=1)  # reset

        return cls(source=src, header=hdr, photometry=phot)

    @classmethod
    def from_photometry(
        cls,
        phot: Photometry,
        *,
        # Required by IES LM-63 spec (no defaults)
        manufacturer: str,
        lumcat: str,
        test: str,
        testlab: str,
        issuedate: str,
        # Optional parameters with sensible defaults
        luminaire: str = None,
        lumens_per_lamp: float = None,
        input_watts: float = 0.0,
        num_lamps: int = 1,
        width: float = 0.0,
        length: float = 0.0,
        height: float = 0.0,
        units: Units = Units.METERS,
        ballast_factor: float = 1.0,
        tilt: Union[str, TiltData] = "NONE",
        version: IESVersion = None,
        file_generation: FileGeneration = None,
        keywords: dict = None,
    ):
        """
        Create an IESFile from photometry data with metadata.

        Per IES LM-63-2002/2019, the following keywords are REQUIRED and must
        be provided by the caller (no defaults):
        - manufacturer: Manufacturer name (MANUFAC keyword)
        - lumcat: Luminaire catalog number (LUMCAT keyword)
        - test: Test report number/description (TEST keyword)
        - testlab: Testing laboratory name (TESTLAB keyword)
        - issuedate: Test completion date, format YYYY-MM-DD (ISSUEDATE keyword)

        Args:
            phot: Photometry object with angular intensity distribution
            manufacturer: Manufacturer name (required)
            lumcat: Luminaire catalog number (required)
            test: Test report number/description (required)
            testlab: Testing laboratory name (required)
            issuedate: Test completion date (required)
            luminaire: Luminaire description (optional, LUMINAIRE keyword)
            lumens_per_lamp: Lumens per lamp (calculated from photometry if None)
            input_watts: Input watts (default 0.0)
            num_lamps: Number of lamps (default 1)
            width: Luminous opening width in meters (default 0.0)
            length: Luminous opening length in meters (default 0.0)
            height: Luminous opening height in meters (default 0.0)
            units: Unit system, FEET or METERS (default METERS)
            ballast_factor: Ballast factor (default 1.0)
            tilt: Tilt information, "NONE" or TiltData (default "NONE")
            version: IES version (default V2019)
            file_generation: FileGeneration flags for V2019 (default: simulated=True)
            keywords: Additional keywords dict to merge

        Returns:
            IESFile with populated header and photometry

        Raises:
            TypeError: If any required parameter is missing

        Example:
            >>> import numpy as np
            >>> from photompy import Photometry, IESFile, PhotometricType
            >>>
            >>> thetas = np.linspace(0, 90, 19)
            >>> phis = np.array([0])
            >>> values = np.cos(np.deg2rad(thetas))[None, :] * 1000
            >>> phot = Photometry(thetas, phis, values, PhotometricType.C)
            >>>
            >>> ies = IESFile.from_photometry(
            ...     phot,
            ...     manufacturer="Acme Lighting",
            ...     lumcat="DL-100",
            ...     test="Test Report 2026-001",
            ...     testlab="Acme Test Lab",
            ...     issuedate="2026-01-27",
            ...     input_watts=15,
            ... )
            >>> ies.write("downlight.ies")
        """
        header = IESHeader.from_photometry(
            phot,
            manufacturer=manufacturer,
            lumcat=lumcat,
            test=test,
            testlab=testlab,
            issuedate=issuedate,
            luminaire=luminaire,
            lumens_per_lamp=lumens_per_lamp,
            input_watts=input_watts,
            num_lamps=num_lamps,
            width=width,
            length=length,
            height=height,
            units=units,
            ballast_factor=ballast_factor,
            tilt=tilt,
            version=version,
            file_generation=file_generation,
            keywords=keywords,
        )
        return cls(source=None, header=header, photometry=phot)

    def update(self, **changes):
        if "multiplier" in changes and changes["multiplier"] != 1:
            raise ValueError(
                "IESFile keeps multiplier fixed at 1. " "Use .scale(factor) instead."
            )
        self.header = self.header.update(**changes)
        return self

    def scale_to_max(self, max_val):
        """scale the photometry to a maximum value"""
        self.photometry.scale_to_max(max_val)
        return self

    def scale_to_total(self, total_power):
        """scale the photometry to a total optical power"""
        self.photometry.scale_to_total(total_power)
        return self

    def scale_to_center(self, center_val):
        """scale the photometry to a center value"""
        self.photometry.scale_to_center(center_val)
        return self

    def scale(self, scale_val):
        """scale the photometry by the given value"""
        self.photometry.scale(scale_val)
        return self

    @property
    def luminous_opening(self):
        """
        Get the luminous opening geometry.

        Returns:
            LuminousOpening object with shape detection and area/volume calculations
        """
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
        which="orig",  # orig | full | interp
        interp_args=(181, 361),
        precision=2,
    ):
        """write the selected photometry to a file, or return as bytes"""

        photometry = self._get_photometry(which, interp_args)
        header = self.header.update(
            num_vert_angles=len(photometry.thetas),
            num_horiz_angles=len(photometry.phis),
        )
        # header
        iesdata = header.to_string()
        # thetas and phis
        iesdata += process_row(photometry.thetas)
        iesdata += process_row(photometry.phis)

        # candela values
        candelas = ""
        for row in photometry.values:
            candelas += process_row(row, sigfigs=precision)
        iesdata += candelas

        # write
        if filename is not None:
            with open(filename, "w", encoding="utf-8") as newfile:
                newfile.write(iesdata)
        else:
            return iesdata.encode("utf-8")

    def plot(
        self,
        plot_type="polar",  # polar | cartesian
        which="full",  # orig | full | interp
        interp_args=(181, 361),  # (num_thetas, num_phis)
        **kwargs,
    ):
        """return a polar or 3d cartesian plot of the photometry"""
        photometry = self._get_photometry(which, interp_args)
        if plot_type.lower() == "polar":
            return photometry.plot_polar(**kwargs)
        elif plot_type.lower() == "cartesian":
            return photometry.plot_cartesian(**kwargs)
        else:
            raise ValueError(f"unrecognized plot type {plot_type}")

    # ---------------- Internals -----------------------
    def _get_photometry(self, which, interp_args=(181, 361)):
        if which.lower() == "orig":
            return self.photometry
        elif which.lower() == "full":
            return self.photometry.expanded()
        elif which.lower() == "interp":
            return self.photometry.interpolated(*interp_args)
        raise ValueError(f"Unknown photometry mode {which}")

    @staticmethod
    def _check_filename(origin, strict=True):
        if origin.suffix.lower() != ".ies":
            msg = f"Unexpected extension {origin.suffix!s}. Expected .ies"
            if strict:
                raise IESPathError(msg)
            else:
                warnings.warn(msg, stacklevel=3)

    @staticmethod
    def _split_string(string):
        """
        Split IES file string into components.

        Returns:
            version: Version line (e.g., "IES:LM-63-2019")
            header: List of header/keyword lines (excluding TILT)
            tilt: "NONE", TiltData object, or filename string
            numeric: List of 13 numeric strings
            blocks: List of remaining data tokens (angles and candela values)
        """
        lines = string.split("\n")
        lines = [line.strip() for line in lines]
        version = lines[0]
        header = []
        tilt = None
        data_start_idx = None

        for i, line in enumerate(lines):
            if line.startswith("TILT="):
                if line == "TILT=INCLUDE":
                    # Parse 4 additional lines after TILT=INCLUDE
                    tilt_lines = lines[i + 1 : i + 5]
                    tilt = TiltData.from_lines(tilt_lines)
                    data_start_idx = i + 5
                elif line == "TILT=NONE":
                    tilt = "NONE"
                    data_start_idx = i + 1
                else:
                    # TILT=<filename>
                    tilt = line.split("=", 1)[1]
                    data_start_idx = i + 1
                break
            else:
                header.append(line)

        if tilt is None:
            raise IESHeaderError("File is malformed; TILT= line missing")

        data = " ".join(lines[data_start_idx:]).split()
        numeric = data[0:13]
        blocks = data[13:]
        return version, header, tilt, numeric, blocks
