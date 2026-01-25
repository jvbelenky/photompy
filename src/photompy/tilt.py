"""
TILT data handling for IES LM-63 files.

Per LM-63-2019 Annex F, TILT describes lamp-to-luminaire geometry for lamps
whose light output varies with tilt angle (e.g., metal halide, HPS).

TILT formats:
- TILT=NONE: No tilt data (most common for LED)
- TILT=INCLUDE: Tilt data embedded in file (4 additional lines)
- TILT=<filename>: Tilt data in separate file (LM-63-2002 only)
"""

from dataclasses import dataclass
from enum import IntEnum
import numpy as np


class LampGeometry(IntEnum):
    """
    Lamp-to-luminaire geometry (LM-63-2019 Annex F).

    Describes how the lamp is mounted relative to the luminaire:
    - VERTICAL_BASE_UP (1): Lamp is vertical with base up (or down)
    - HORIZONTAL (2): Lamp is horizontal, remains horizontal when luminaire tilts
    - TILTS_WITH_LUMINAIRE (3): Lamp is horizontal, tilts with luminaire
    """

    VERTICAL_BASE_UP = 1
    HORIZONTAL = 2
    TILTS_WITH_LUMINAIRE = 3


@dataclass(slots=True)
class TiltData:
    """
    TILT=INCLUDE data for lamp-to-luminaire geometry.

    Attributes:
        geometry: Lamp-to-luminaire geometry type (1, 2, or 3)
        angles: Array of tilt angles in degrees
        factors: Array of multiplying factors corresponding to each angle
    """

    geometry: LampGeometry
    angles: np.ndarray
    factors: np.ndarray

    def __post_init__(self):
        """Validate and convert arrays."""
        self.angles = np.asarray(self.angles, dtype=float)
        self.factors = np.asarray(self.factors, dtype=float)

        if len(self.angles) != len(self.factors):
            raise ValueError(
                f"angles ({len(self.angles)}) and factors ({len(self.factors)}) "
                "must have the same length"
            )

        if not isinstance(self.geometry, LampGeometry):
            self.geometry = LampGeometry(self.geometry)

    def get_factor(self, angle: float) -> float:
        """
        Interpolate the multiplying factor for an arbitrary tilt angle.

        Args:
            angle: Tilt angle in degrees

        Returns:
            Interpolated multiplying factor
        """
        return float(np.interp(angle, self.angles, self.factors))

    @classmethod
    def from_lines(cls, lines: list[str]) -> "TiltData":
        """
        Parse TiltData from 4 lines after TILT=INCLUDE.

        Args:
            lines: List of 4 strings:
                [0] lamp-to-luminaire geometry (1, 2, or 3)
                [1] number of tilt angles
                [2] tilt angles (space-separated)
                [3] multiplying factors (space-separated)

        Returns:
            TiltData instance
        """
        if len(lines) < 4:
            raise ValueError(f"Expected 4 lines for TILT=INCLUDE, got {len(lines)}")

        geometry = int(lines[0].strip())
        num_angles = int(lines[1].strip())
        angles = np.array(lines[2].split(), dtype=float)
        factors = np.array(lines[3].split(), dtype=float)

        if len(angles) != num_angles:
            raise ValueError(
                f"Expected {num_angles} angles, got {len(angles)}"
            )
        if len(factors) != num_angles:
            raise ValueError(
                f"Expected {num_angles} factors, got {len(factors)}"
            )

        return cls(geometry=LampGeometry(geometry), angles=angles, factors=factors)

    def to_lines(self) -> list[str]:
        """
        Convert TiltData to lines for writing to IES file.

        Returns:
            List of 4 strings ready to be written after TILT=INCLUDE
        """
        return [
            str(int(self.geometry)),
            str(len(self.angles)),
            " ".join(str(a) for a in self.angles),
            " ".join(str(f) for f in self.factors),
        ]

    def __eq__(self, other):
        if not isinstance(other, TiltData):
            return NotImplemented
        return (
            self.geometry == other.geometry
            and np.array_equal(self.angles, other.angles)
            and np.array_equal(self.factors, other.factors)
        )
