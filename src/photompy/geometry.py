"""
Luminous Opening Geometry per LM-63-19 Section 5.10-5.11.

This module implements full luminous opening shape detection, area/volume
calculations, and geometry helpers based on the IESNA LM-63-2019 standard.

Per Section 5.10-5.11 and Table 1, the sign of dimensions encodes the shape:
- Positive values = rectangular/squared edges
- Negative values = rounded edges (when two dimensions in a plane are both negative)
- Zero values = no dimension in that direction
"""

from dataclasses import dataclass
from enum import Enum, auto
import math


class LuminousShape(Enum):
    """
    Luminous opening shapes per LM-63-19 Table 1.

    Shape detection is based on the sign pattern of (width, length, height):
    - Positive = rectangular/squared edge
    - Negative = rounded edge (in that plane)
    - Zero = no dimension

    When width == length (in absolute value), shapes are circular/spherical.
    When width != length, shapes are elliptical.
    """

    POINT = auto()
    RECTANGULAR = auto()
    RECTANGULAR_WITH_SIDES = auto()
    CIRCULAR = auto()
    ELLIPSE = auto()
    VERTICAL_CYLINDER = auto()
    VERTICAL_ELLIPTICAL_CYLINDER = auto()
    SPHERE = auto()
    ELLIPSOIDAL_SPHEROID = auto()
    HORIZONTAL_CYLINDER_ALONG = auto()  # along photometric horizontal
    HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG = auto()
    HORIZONTAL_CYLINDER_PERPENDICULAR = auto()  # perpendicular to phot. horiz.
    HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR = auto()
    VERTICAL_CIRCLE = auto()
    VERTICAL_ELLIPSE = auto()


def _sign(x: float) -> int:
    """Return sign of x: -1, 0, or 1."""
    if x > 0:
        return 1
    elif x < 0:
        return -1
    return 0


def _detect_shape(w: float, l: float, h: float) -> LuminousShape:
    """
    Detect shape from dimension sign pattern.

    Sign patterns per LM-63-19 Table 1:
    - (0, 0, 0) = POINT
    - (+, +, 0) = RECTANGULAR
    - (+, +, +) = RECTANGULAR_WITH_SIDES
    - (-, -, 0) = CIRCULAR or ELLIPSE (circular if |w|==|l|)
    - (-, -, +) = VERTICAL_CYLINDER or VERTICAL_ELLIPTICAL_CYLINDER
    - (-, -, -) = SPHERE or ELLIPSOIDAL_SPHEROID
    - (-, +, -) = HORIZONTAL_CYLINDER_ALONG or HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG
    - (+, -, -) = HORIZONTAL_CYLINDER_PERPENDICULAR or HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR
    - (-, 0, -) = VERTICAL_CIRCLE or VERTICAL_ELLIPSE
    """
    sw, sl, sh = _sign(w), _sign(l), _sign(h)

    # Check for circular vs elliptical based on equal magnitudes
    is_wl_equal = math.isclose(abs(w), abs(l), rel_tol=1e-9, abs_tol=1e-12)
    is_wh_equal = math.isclose(abs(w), abs(h), rel_tol=1e-9, abs_tol=1e-12)
    is_all_equal = is_wl_equal and is_wh_equal

    # Point: all zero
    if sw == 0 and sl == 0 and sh == 0:
        return LuminousShape.POINT

    # Rectangular: (+, +, 0)
    if sw > 0 and sl > 0 and sh == 0:
        return LuminousShape.RECTANGULAR

    # Rectangular with Luminous Sides: (+, +, +)
    if sw > 0 and sl > 0 and sh > 0:
        return LuminousShape.RECTANGULAR_WITH_SIDES

    # Circular/Ellipse: (-, -, 0)
    if sw < 0 and sl < 0 and sh == 0:
        return LuminousShape.CIRCULAR if is_wl_equal else LuminousShape.ELLIPSE

    # Vertical Cylinder: (-, -, +)
    if sw < 0 and sl < 0 and sh > 0:
        return (
            LuminousShape.VERTICAL_CYLINDER
            if is_wl_equal
            else LuminousShape.VERTICAL_ELLIPTICAL_CYLINDER
        )

    # Sphere/Spheroid: (-, -, -)
    if sw < 0 and sl < 0 and sh < 0:
        return (
            LuminousShape.SPHERE if is_all_equal else LuminousShape.ELLIPSOIDAL_SPHEROID
        )

    # Horizontal Cylinder Along Photometric Horizontal: (-, +, -)
    if sw < 0 and sl > 0 and sh < 0:
        return (
            LuminousShape.HORIZONTAL_CYLINDER_ALONG
            if is_wh_equal
            else LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG
        )

    # Horizontal Cylinder Perpendicular to Photometric Horizontal: (+, -, -)
    if sw > 0 and sl < 0 and sh < 0:
        is_lh_equal = math.isclose(abs(l), abs(h), rel_tol=1e-9, abs_tol=1e-12)
        return (
            LuminousShape.HORIZONTAL_CYLINDER_PERPENDICULAR
            if is_lh_equal
            else LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR
        )

    # Vertical Circle/Ellipse Facing Photometric Horizontal: (-, 0, -)
    if sw < 0 and sl == 0 and sh < 0:
        return (
            LuminousShape.VERTICAL_CIRCLE
            if is_wh_equal
            else LuminousShape.VERTICAL_ELLIPSE
        )

    # Default fallback to point for unrecognized patterns
    return LuminousShape.POINT


# Unit conversion factors (to meters)
_UNIT_FACTORS = {
    "meters": 1.0,
    "m": 1.0,
    "feet": 0.3048,
    "ft": 0.3048,
    "inches": 0.0254,
    "in": 0.0254,
    "cm": 0.01,
    "centimeters": 0.01,
    "mm": 0.001,
    "millimeters": 0.001,
}


@dataclass(frozen=True, slots=True)
class LuminousOpening:
    """
    Luminous opening geometry per LM-63-19 Section 5.10-5.11.

    The sign of width, length, height encodes the shape:
    - Positive = rectangular/squared edge
    - Negative = rounded edge (in that plane)
    - Zero = no dimension

    All dimensions are stored in meters internally.

    Attributes:
        width: Width perpendicular to 0-degree photometric plane (meters)
        length: Length parallel to 0-degree plane, along phot. horizontal (meters)
        height: Height parallel to photometric zero, vertical (meters)
    """

    width: float  # perpendicular to 0-degree photometric plane
    length: float  # parallel to 0-degree plane (along phot. horizontal)
    height: float  # parallel to photometric zero (vertical)

    @classmethod
    def from_header(
        cls, width: float, length: float, height: float, units: int
    ) -> "LuminousOpening":
        """
        Create from IES header values, converting to meters.

        Args:
            width: Width value from IES header
            length: Length value from IES header
            height: Height value from IES header
            units: Unit code (1=feet, 2=meters)

        Returns:
            LuminousOpening instance with dimensions in meters
        """
        if units == 1:  # feet
            factor = 0.3048
        else:  # meters (units == 2)
            factor = 1.0

        return cls(
            width=width * factor,
            length=length * factor,
            height=height * factor,
        )

    @property
    def shape(self) -> LuminousShape:
        """Determine the luminous opening shape from dimension signs."""
        return _detect_shape(self.width, self.length, self.height)

    @property
    def is_point(self) -> bool:
        """True if all dimensions are zero (point source)."""
        return self.shape == LuminousShape.POINT

    @property
    def is_circular(self) -> bool:
        """
        True if shape is circular (not elliptical).

        This includes circular, spherical, and cylindrical shapes
        where |width| == |length| or |width| == |height| as appropriate.
        """
        return self.shape in (
            LuminousShape.CIRCULAR,
            LuminousShape.SPHERE,
            LuminousShape.VERTICAL_CYLINDER,
            LuminousShape.HORIZONTAL_CYLINDER_ALONG,
            LuminousShape.HORIZONTAL_CYLINDER_PERPENDICULAR,
            LuminousShape.VERTICAL_CIRCLE,
        )

    @property
    def is_rectangular(self) -> bool:
        """True if shape is rectangular (no rounded edges)."""
        return self.shape in (
            LuminousShape.RECTANGULAR,
            LuminousShape.RECTANGULAR_WITH_SIDES,
        )

    @property
    def is_3d(self) -> bool:
        """True if shape has volume (not flat)."""
        return self.shape in (
            LuminousShape.RECTANGULAR_WITH_SIDES,
            LuminousShape.VERTICAL_CYLINDER,
            LuminousShape.VERTICAL_ELLIPTICAL_CYLINDER,
            LuminousShape.SPHERE,
            LuminousShape.ELLIPSOIDAL_SPHEROID,
            LuminousShape.HORIZONTAL_CYLINDER_ALONG,
            LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG,
            LuminousShape.HORIZONTAL_CYLINDER_PERPENDICULAR,
            LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR,
        )

    def area(self, surface: str = "opening") -> float:
        """
        Calculate area in square meters.

        Args:
            surface: "opening" for luminous opening area (default),
                     "total" for total surface area (3D shapes only)

        Returns:
            Area in square meters
        """
        w, l, h = abs(self.width), abs(self.length), abs(self.height)
        shape = self.shape

        if shape == LuminousShape.POINT:
            return 0.0

        elif shape == LuminousShape.RECTANGULAR:
            return w * l

        elif shape == LuminousShape.RECTANGULAR_WITH_SIDES:
            if surface == "opening":
                return w * l
            else:  # total surface area
                return 2 * (w * l + w * h + l * h)

        elif shape == LuminousShape.CIRCULAR:
            # Diameter stored in width (and length)
            r = w / 2
            return math.pi * r * r

        elif shape == LuminousShape.ELLIPSE:
            # Semi-axes
            return math.pi * (w / 2) * (l / 2)

        elif shape == LuminousShape.VERTICAL_CYLINDER:
            r = w / 2
            if surface == "opening":
                return math.pi * r * r  # top circular opening
            else:  # total surface area
                return 2 * math.pi * r * r + 2 * math.pi * r * h

        elif shape == LuminousShape.VERTICAL_ELLIPTICAL_CYLINDER:
            a, b = w / 2, l / 2
            if surface == "opening":
                return math.pi * a * b  # top elliptical opening
            else:  # total surface area (approximate lateral)
                ellipse_area = math.pi * a * b
                # Ramanujan approximation for ellipse perimeter
                perimeter = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
                return 2 * ellipse_area + perimeter * h

        elif shape == LuminousShape.SPHERE:
            r = w / 2
            if surface == "opening":
                return math.pi * r * r  # projected circular area
            else:  # total surface area
                return 4 * math.pi * r * r

        elif shape == LuminousShape.ELLIPSOIDAL_SPHEROID:
            a, b, c = w / 2, l / 2, h / 2
            if surface == "opening":
                return math.pi * a * b  # projected elliptical area
            else:  # approximate total surface area (Thomsen formula)
                p = 1.6075
                return (
                    4
                    * math.pi
                    * (
                        ((a * b) ** p + (a * c) ** p + (b * c) ** p) / 3
                    ) ** (1 / p)
                )

        elif shape == LuminousShape.HORIZONTAL_CYLINDER_ALONG:
            r = w / 2
            if surface == "opening":
                return math.pi * r * r  # circular end
            else:  # total surface area
                return 2 * math.pi * r * r + 2 * math.pi * r * l

        elif shape == LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG:
            a, c = w / 2, h / 2
            if surface == "opening":
                return math.pi * a * c  # elliptical end
            else:
                ellipse_area = math.pi * a * c
                perimeter = math.pi * (3 * (a + c) - math.sqrt((3 * a + c) * (a + 3 * c)))
                return 2 * ellipse_area + perimeter * l

        elif shape == LuminousShape.HORIZONTAL_CYLINDER_PERPENDICULAR:
            r = l / 2
            if surface == "opening":
                return math.pi * r * r  # circular end
            else:
                return 2 * math.pi * r * r + 2 * math.pi * r * w

        elif shape == LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR:
            b, c = l / 2, h / 2
            if surface == "opening":
                return math.pi * b * c
            else:
                ellipse_area = math.pi * b * c
                perimeter = math.pi * (3 * (b + c) - math.sqrt((3 * b + c) * (b + 3 * c)))
                return 2 * ellipse_area + perimeter * w

        elif shape == LuminousShape.VERTICAL_CIRCLE:
            r = w / 2
            return math.pi * r * r

        elif shape == LuminousShape.VERTICAL_ELLIPSE:
            return math.pi * (w / 2) * (h / 2)

        return 0.0

    def volume(self) -> float:
        """
        Calculate volume in cubic meters.

        Returns:
            Volume in cubic meters (0 for 2D shapes)
        """
        w, l, h = abs(self.width), abs(self.length), abs(self.height)
        shape = self.shape

        if shape == LuminousShape.RECTANGULAR_WITH_SIDES:
            return w * l * h

        elif shape == LuminousShape.VERTICAL_CYLINDER:
            r = w / 2
            return math.pi * r * r * h

        elif shape == LuminousShape.VERTICAL_ELLIPTICAL_CYLINDER:
            return math.pi * (w / 2) * (l / 2) * h

        elif shape == LuminousShape.SPHERE:
            r = w / 2
            return (4 / 3) * math.pi * r * r * r

        elif shape == LuminousShape.ELLIPSOIDAL_SPHEROID:
            return (4 / 3) * math.pi * (w / 2) * (l / 2) * (h / 2)

        elif shape == LuminousShape.HORIZONTAL_CYLINDER_ALONG:
            r = w / 2
            return math.pi * r * r * l

        elif shape == LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG:
            return math.pi * (w / 2) * (h / 2) * l

        elif shape == LuminousShape.HORIZONTAL_CYLINDER_PERPENDICULAR:
            r = l / 2
            return math.pi * r * r * w

        elif shape == LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR:
            return math.pi * (l / 2) * (h / 2) * w

        # 2D shapes have no volume
        return 0.0

    def perimeter(self) -> float:
        """
        Calculate perimeter of the opening in meters.

        For 3D shapes, returns the perimeter of the primary opening face.

        Returns:
            Perimeter in meters
        """
        w, l, h = abs(self.width), abs(self.length), abs(self.height)
        shape = self.shape

        if shape == LuminousShape.POINT:
            return 0.0

        elif shape in (LuminousShape.RECTANGULAR, LuminousShape.RECTANGULAR_WITH_SIDES):
            return 2 * (w + l)

        elif shape in (LuminousShape.CIRCULAR, LuminousShape.VERTICAL_CYLINDER):
            return math.pi * w  # pi * diameter

        elif shape in (LuminousShape.ELLIPSE, LuminousShape.VERTICAL_ELLIPTICAL_CYLINDER):
            a, b = w / 2, l / 2
            # Ramanujan approximation for ellipse perimeter
            return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))

        elif shape == LuminousShape.SPHERE:
            return math.pi * w  # great circle perimeter

        elif shape == LuminousShape.ELLIPSOIDAL_SPHEROID:
            a, b = w / 2, l / 2
            return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))

        elif shape == LuminousShape.HORIZONTAL_CYLINDER_ALONG:
            return math.pi * w

        elif shape == LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG:
            a, c = w / 2, h / 2
            return math.pi * (3 * (a + c) - math.sqrt((3 * a + c) * (a + 3 * c)))

        elif shape == LuminousShape.HORIZONTAL_CYLINDER_PERPENDICULAR:
            return math.pi * l

        elif shape == LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR:
            b, c = l / 2, h / 2
            return math.pi * (3 * (b + c) - math.sqrt((3 * b + c) * (b + 3 * c)))

        elif shape == LuminousShape.VERTICAL_CIRCLE:
            return math.pi * w

        elif shape == LuminousShape.VERTICAL_ELLIPSE:
            a, c = w / 2, h / 2
            return math.pi * (3 * (a + c) - math.sqrt((3 * a + c) * (a + 3 * c)))

        return 0.0

    @property
    def effective_diameter(self) -> float:
        """
        Diameter of a circle with equivalent opening area.

        Returns:
            Effective diameter in meters
        """
        area = self.area(surface="opening")
        if area <= 0:
            return 0.0
        return 2 * math.sqrt(area / math.pi)

    def area_in(self, units: str) -> float:
        """
        Get area in specified units squared.

        Args:
            units: "meters", "m", "feet", "ft", "inches", "in",
                   "cm", "centimeters", "mm", "millimeters"

        Returns:
            Area in the specified units squared
        """
        units_lower = units.lower()
        if units_lower not in _UNIT_FACTORS:
            raise ValueError(
                f"Unknown units: {units!r}. "
                f"Supported: {', '.join(_UNIT_FACTORS.keys())}"
            )

        factor = _UNIT_FACTORS[units_lower]
        # Area converts by factor^2
        return self.area() / (factor * factor)

    def volume_in(self, units: str) -> float:
        """
        Get volume in specified units cubed.

        Args:
            units: "meters", "m", "feet", "ft", "inches", "in",
                   "cm", "centimeters", "mm", "millimeters"

        Returns:
            Volume in the specified units cubed
        """
        units_lower = units.lower()
        if units_lower not in _UNIT_FACTORS:
            raise ValueError(
                f"Unknown units: {units!r}. "
                f"Supported: {', '.join(_UNIT_FACTORS.keys())}"
            )

        factor = _UNIT_FACTORS[units_lower]
        # Volume converts by factor^3
        return self.volume() / (factor * factor * factor)

    def dimensions_in(self, units: str) -> tuple[float, float, float]:
        """
        Get (width, length, height) in specified units.

        Signs are preserved to indicate the shape encoding.

        Args:
            units: "meters", "m", "feet", "ft", "inches", "in",
                   "cm", "centimeters", "mm", "millimeters"

        Returns:
            Tuple of (width, length, height) in the specified units
        """
        units_lower = units.lower()
        if units_lower not in _UNIT_FACTORS:
            raise ValueError(
                f"Unknown units: {units!r}. "
                f"Supported: {', '.join(_UNIT_FACTORS.keys())}"
            )

        factor = _UNIT_FACTORS[units_lower]
        return (
            self.width / factor,
            self.length / factor,
            self.height / factor,
        )

    def __repr__(self) -> str:
        return (
            f"LuminousOpening(width={self.width}, length={self.length}, "
            f"height={self.height}, shape={self.shape.name})"
        )
