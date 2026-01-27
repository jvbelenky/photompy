from dataclasses import dataclass, asdict, replace
from enum import IntEnum, StrEnum
from datetime import date
from typing import Union
import warnings
from .exceptions import IESHeaderError
from .photometry import PhotometricType
from .tilt import TiltData


@dataclass(frozen=True, slots=True)
class FileGeneration:
    """
    File Generation Type per LM-63-2019 Section 5.13.

    Encodes metadata about how the photometric data was created:
    - accredited: Whether data was measured by an accredited lab
    - simulated: Whether data was generated/simulated (vs. measured)
    - interpolated: Whether data has been interpolated from original measurements
    - scaled: Whether data has been scaled from original measurements

    The value is encoded as 1.XYZAB where:
    - X: 0=not accredited, 1=accredited lab
    - Y: 0=measured, 1=simulated
    - Z: Reserved (always 0)
    - A: 0=not interpolated, 1=interpolated
    - B: 0=not scaled, 1=scaled
    """

    accredited: bool = False
    simulated: bool = False
    interpolated: bool = False
    scaled: bool = False

    @classmethod
    def from_float(cls, val: float) -> "FileGeneration":
        """
        Parse 1.XYZAB format.

        Args:
            val: Float value like 1.10011 or 1.00001

        Returns:
            FileGeneration instance
        """
        # Handle the special "undefined" value
        if val == 1.00001:
            return cls()  # All False (undefined)

        # Format to 5 decimal places and extract digits
        s = f"{val:.5f}"
        parts = s.split(".")
        if len(parts) != 2 or parts[0] != "1":
            return cls()  # Invalid format, return undefined

        digits = parts[1].ljust(5, "0")  # Pad to 5 digits

        return cls(
            accredited=(digits[0] == "1"),
            simulated=(digits[1] == "1"),
            # digits[2] is reserved (Z)
            interpolated=(digits[3] == "1"),
            scaled=(digits[4] == "1"),
        )

    def to_float(self) -> float:
        """
        Convert back to 1.XYZAB format.

        Returns:
            Float value like 1.10011
        """
        x = "1" if self.accredited else "0"
        y = "1" if self.simulated else "0"
        z = "0"  # Reserved
        a = "1" if self.interpolated else "0"
        b = "1" if self.scaled else "0"
        return float(f"1.{x}{y}{z}{a}{b}")

    @property
    def is_undefined(self) -> bool:
        """Check if this represents the 'undefined' state (1.00001)."""
        return not any([self.accredited, self.simulated,
                        self.interpolated, self.scaled])

    def __str__(self) -> str:
        if self.is_undefined:
            return "FileGeneration(undefined)"
        parts = []
        if self.accredited:
            parts.append("accredited")
        if self.simulated:
            parts.append("simulated")
        if self.interpolated:
            parts.append("interpolated")
        if self.scaled:
            parts.append("scaled")
        return f"FileGeneration({', '.join(parts)})"


class Units(IntEnum):
    FEET = 1
    METERS = 2


class IESVersion(StrEnum):
    V2002 = "LM-63-2002"
    V2019 = "LM-63-2019"
    UNKNOWN = "UNKNOWN"

    @property
    def supports_filegen(self) -> bool:
        return self is IESVersion.V2019

    @property
    def supports_tilt_file(self) -> bool:
        return self is IESVersion.V2002

    @classmethod
    def from_token(cls, token: str, *, strict: bool = True):
        token = token.split(":")[1].strip().upper()
        try:
            return cls(token)
        except ValueError:
            msg = f"Unsupported IES version {token!r}"
            if strict:
                raise IESHeaderError(msg)
            else:
                warnings.warn(msg)
            return cls.UNKNOWN

    def to_header(self) -> str:
        if self is IESVersion.V2019:
            return "IES:" + self.value
        elif self is IESVersion.V2002:
            return "IESNA:" + self.value
        else:
            return "VERSION UNKNOWN"


# class FileGeneration(Enum):
# UNDEFINED = 1.00001
# SIMULATED = 1.00010
# UNACCREDITED = 1.00000
# UNACCREDITED_SCALED = 1.00100
# UNACCREDITED_INTERP = 1.01000
# UNACCREDITED_INTERP_SCALED = 1.01100
# ACCREDITED = 1.10000
# ACCREDITED_SCALED = 1.10100
# ACCREDITED_INTERP = 1.11000
# ACCREDITED_INTERP_SCALED = 1.11100


@dataclass(frozen=True, slots=True)
class IESHeader:
    version: str
    keywords: dict
    tilt: Union[str, TiltData, None]  # "NONE" | TiltData | filename
    num_lamps: int
    lumens_per_lamp: float
    multiplier: float
    num_vert_angles: int
    num_horiz_angles: int
    photometric_type: PhotometricType  # IntEnum → C/B/A
    units: Units  # IntEnum → FEET/METERS
    width: float
    length: float
    height: float
    ballast_factor: float
    _v11: float
    input_watts: float

    @property
    def file_generation_type(self) -> FileGeneration:
        """
        Get the file generation type as a FileGeneration object (LM-63-2019 only).

        Returns:
            FileGeneration object with accredited, simulated, interpolated, scaled flags
        """
        if self.version.supports_filegen:
            return FileGeneration.from_float(self._v11)
        raise AttributeError(
            "file_generation_type is not defined for version LM-63-2002"
        )

    @property
    def future_use(self):
        return self._v11

    @property
    def luminous_opening(self):
        """
        Get the luminous opening geometry.

        Returns:
            LuminousOpening object with shape detection and area/volume calculations
        """
        from .geometry import LuminousOpening

        return LuminousOpening.from_header(
            self.width, self.length, self.height, self.units
        )

    @classmethod
    def from_tokens(
        cls,
        version: str,
        numeric: list,  # 13 tokens as strings
        keywords: dict,
        tilt: Union[str, TiltData, None] = "NONE",
        strict: bool = True,
    ):

        nums = list(map(float, numeric))

        try:
            pt = PhotometricType(int(nums[5]))
        except ValueError as e:
            msg = f"Bad photometric code: {e}"
            if strict:
                raise IESHeaderError(msg) from None
            pt = PhotometricType.C  # guess
            warnings.warn(msg, stacklevel=3)

        try:
            units = Units(int(nums[6]))
        except ValueError as e:
            msg = f"Bad units code: {e}"
            if strict:
                raise IESHeaderError(msg) from None
            units = Units.FEET  # guess
            warnings.warn(msg, stacklevel=3)

        # # version-dependent interpretation of column 11 --------------
        # if version.endswith("2019"):
        # try:
        # v11 = FileGeneration(nums[11])
        # except ValueError:
        # msg = "Invalid file_generation_type value"
        # if strict:
        # raise IESHeaderError(msg)
        # else:
        # warnings.warn(msg)
        # v11 = FileGeneration.UNDEFINED  # fallback / guess
        # else:  # 2002 or earlier
        # v11 = nums[11]

        return cls(
            version=version,
            keywords=keywords,
            tilt=tilt,
            num_lamps=int(nums[0]),
            lumens_per_lamp=nums[1],
            multiplier=nums[2],
            num_vert_angles=int(nums[3]),
            num_horiz_angles=int(nums[4]),
            photometric_type=pt,  # IntEnum → C/B/A
            units=units,  # IntEnum → FEET/METERS
            width=nums[7],
            length=nums[8],
            height=nums[9],
            ballast_factor=nums[10],
            _v11=nums[11],
            input_watts=nums[12],
        )

    @classmethod
    def from_photometry(
        cls,
        phot,
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
        version: "IESVersion" = None,
        file_generation: FileGeneration = None,
        keywords: dict = None,
    ):
        """
        Create an IES header from photometry data with metadata.

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
            IESHeader with populated fields

        Raises:
            TypeError: If any required parameter is missing
        """
        if version is None:
            version = IESVersion.V2019

        # Build keywords dict with required fields
        kw = {
            "TEST": test,
            "TESTLAB": testlab,
            "ISSUEDATE": issuedate,
            "MANUFAC": manufacturer,
            "LUMCAT": lumcat,
        }
        if luminaire is not None:
            kw["LUMINAIRE"] = luminaire
        if keywords is not None:
            kw.update(keywords)

        # Calculate lumens_per_lamp from photometry if not provided
        if lumens_per_lamp is None:
            lumens_per_lamp = phot.total_optical_power() / num_lamps

        # File generation type for V2019
        if file_generation is None:
            file_generation = FileGeneration(simulated=True)
        v11 = file_generation.to_float() if version.supports_filegen else 1.0

        return cls(
            version=version,
            keywords=kw,
            tilt=tilt,
            num_lamps=num_lamps,
            lumens_per_lamp=lumens_per_lamp,
            multiplier=1.0,
            num_vert_angles=len(phot.thetas),
            num_horiz_angles=len(phot.phis),
            photometric_type=phot.photometric_type,
            units=units,
            width=width,
            length=length,
            height=height,
            ballast_factor=ballast_factor,
            _v11=v11,
            input_watts=input_watts,
        )

    def to_dict(self):
        """return as dict"""
        return asdict(self)

    def to_float(self) -> list:
        dct = self.to_dict()
        dct.pop("version", None)
        dct.pop("keywords", None)
        dct.pop("tilt", None)
        return [float(val) for val in dct.values()]

    def numeric_to_string(self):
        """return the numeric/non-keyword strings"""
        dct = self.to_dict()
        dct.pop("version", None)
        dct.pop("keywords", None)
        dct.pop("tilt", None)
        return [str(val) for val in dct.values()]

    def to_string(self):
        """convert header to a string ready for writing to a file"""
        # top of the file
        iesdata = self.version.to_header() + "\n"
        # keywords
        for key, val in self.keywords.items():
            if key != "TILT":
                iesdata += f"[{key}] {val}\n"
        # TILT line(s)
        iesdata += self._tilt_to_string()
        # numeric line
        numeric = self.numeric_to_string()
        iesdata += " ".join(numeric[0:10]) + "\n"
        iesdata += " ".join(numeric[10:13]) + "\n"
        return iesdata

    def _tilt_to_string(self) -> str:
        """Convert tilt data to string for writing."""
        if self.tilt is None or self.tilt == "NONE":
            return "TILT=NONE\n"
        elif isinstance(self.tilt, TiltData):
            lines = ["TILT=INCLUDE"]
            lines.extend(self.tilt.to_lines())
            return "\n".join(lines) + "\n"
        else:
            # TILT=<filename> (LM-63-2002 only)
            return f"TILT={self.tilt}\n"

    def update(self, **changes):
        if changes.get("units") is not None:
            changes.setdefault("units", Units(changes["units"]))
        return replace(self, **changes)
