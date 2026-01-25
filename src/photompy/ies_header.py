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
    def from_photometry(cls, phot):
        """
        Create a minimal, spec-compliant header for a standalone Photometry.
        Only the angle counts, multiplier, and photometric type are real;
        all other numeric fields get neutral placeholders.
        """
        today = date.today().isoformat()

        keywords = {
            "TEST": "GENERATED PHOTOMETRY",
            "TESTLAB": "PhotomPy",
            "ISSUEDATE": today,
            "MANUFAC": "PhotomPy",  # todo: add version
        }

        return cls(
            version=IESVersion.V2019,
            keywords=keywords,
            tilt="NONE",
            num_lamps=1,
            lumens_per_lamp=1.0,
            multiplier=1.0,
            num_vert_angles=len(phot.thetas),
            num_horiz_angles=len(phot.phis),
            photometric_type=phot.photometric_type,
            units=Units.METERS,
            width=0.0,
            length=0.0,
            height=0.0,
            ballast_factor=1.0,
            _v11=1.00001,  # Undefined file generation
            input_watts=0.0,
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
