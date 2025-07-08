from dataclasses import dataclass, asdict, replace
from enum import IntEnum, StrEnum
from datetime import date
import warnings
from .exceptions import IESHeaderError
from .photometry import PhotometricType


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
    # tilt: str | None  # NONE | Include | Path
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
    def file_generation_type(self):
        if self.version.supports_filegen:
            return self._v11
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
        # tilt: str,  # temp! currently just a raw string
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

        # TODO: processing of TILT goes here

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
            # tilt=tilt,
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
            # tilt="NONE",
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

    def numeric_to_string(self):
        """return the numeric/non-keyword strings"""
        return [str(val) for val in self.to_dict().values()][2:]

    def to_string(self):
        """convert header to a string ready for writing to a file"""
        # top of the file
        iesdata = self.version.to_header() + "\n"
        # header
        for key, val in self.keywords.items():
            if key != "TILT":
                iesdata += f"[{key}] {val}\n"
            else:
                iesdata += f"{key}={val}\n"
        numeric = self.numeric_to_string()
        iesdata += " ".join(numeric[0:10]) + "\n"
        iesdata += " ".join(numeric[10:13]) + "\n"
        return iesdata

    def update(self, **changes):
        if changes.get("units") is not None:
            changes.setdefault("units", Units(changes["units"]))
        return replace(self, **changes)
