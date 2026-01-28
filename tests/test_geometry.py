"""Tests for Luminous Opening Geometry (LM-63-19 Section 5.10-5.11)."""

import math
import pytest
from pathlib import Path

from photompy import IESFile
from photompy.geometry import LuminousOpening, LuminousShape


@pytest.fixture
def sample_path():
    return Path(__file__).parent / "data"


class TestLuminousShape:
    """Tests for LuminousShape enum."""

    def test_all_shapes_exist(self):
        """All 15 shapes per LM-63-19 Table 1 should exist."""
        assert LuminousShape.POINT
        assert LuminousShape.RECTANGULAR
        assert LuminousShape.RECTANGULAR_WITH_SIDES
        assert LuminousShape.CIRCULAR
        assert LuminousShape.ELLIPSE
        assert LuminousShape.VERTICAL_CYLINDER
        assert LuminousShape.VERTICAL_ELLIPTICAL_CYLINDER
        assert LuminousShape.SPHERE
        assert LuminousShape.ELLIPSOIDAL_SPHEROID
        assert LuminousShape.HORIZONTAL_CYLINDER_ALONG
        assert LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG
        assert LuminousShape.HORIZONTAL_CYLINDER_PERPENDICULAR
        assert LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR
        assert LuminousShape.VERTICAL_CIRCLE
        assert LuminousShape.VERTICAL_ELLIPSE


class TestShapeDetection:
    """Tests for shape detection from dimension signs."""

    def test_point_shape(self):
        """(0, 0, 0) should be POINT."""
        lo = LuminousOpening(0, 0, 0)
        assert lo.shape == LuminousShape.POINT
        assert lo.is_point

    def test_rectangular_shape(self):
        """(+W, +L, 0) should be RECTANGULAR."""
        lo = LuminousOpening(0.1, 0.2, 0)
        assert lo.shape == LuminousShape.RECTANGULAR
        assert lo.is_rectangular
        assert not lo.is_circular
        assert not lo.is_3d

    def test_rectangular_with_sides(self):
        """(+W, +L, +H) should be RECTANGULAR_WITH_SIDES."""
        lo = LuminousOpening(0.1, 0.2, 0.05)
        assert lo.shape == LuminousShape.RECTANGULAR_WITH_SIDES
        assert lo.is_rectangular
        assert lo.is_3d

    def test_circular_shape(self):
        """(-D, -D, 0) should be CIRCULAR."""
        lo = LuminousOpening(-0.1, -0.1, 0)
        assert lo.shape == LuminousShape.CIRCULAR
        assert lo.is_circular
        assert not lo.is_rectangular
        assert not lo.is_3d

    def test_ellipse_shape(self):
        """(-W, -L, 0) with W != L should be ELLIPSE."""
        lo = LuminousOpening(-0.1, -0.2, 0)
        assert lo.shape == LuminousShape.ELLIPSE
        assert not lo.is_circular

    def test_vertical_cylinder(self):
        """(-D, -D, +H) should be VERTICAL_CYLINDER."""
        lo = LuminousOpening(-0.1, -0.1, 0.2)
        assert lo.shape == LuminousShape.VERTICAL_CYLINDER
        assert lo.is_circular
        assert lo.is_3d

    def test_vertical_elliptical_cylinder(self):
        """(-W, -L, +H) with W != L should be VERTICAL_ELLIPTICAL_CYLINDER."""
        lo = LuminousOpening(-0.1, -0.2, 0.3)
        assert lo.shape == LuminousShape.VERTICAL_ELLIPTICAL_CYLINDER
        assert not lo.is_circular
        assert lo.is_3d

    def test_sphere(self):
        """(-D, -D, -D) should be SPHERE."""
        lo = LuminousOpening(-0.1, -0.1, -0.1)
        assert lo.shape == LuminousShape.SPHERE
        assert lo.is_circular
        assert lo.is_3d

    def test_ellipsoidal_spheroid(self):
        """(-W, -L, -H) with any unequal should be ELLIPSOIDAL_SPHEROID."""
        lo = LuminousOpening(-0.1, -0.2, -0.15)
        assert lo.shape == LuminousShape.ELLIPSOIDAL_SPHEROID
        assert not lo.is_circular
        assert lo.is_3d

    def test_horizontal_cylinder_along(self):
        """(-D, +L, -D) should be HORIZONTAL_CYLINDER_ALONG."""
        lo = LuminousOpening(-0.1, 0.5, -0.1)
        assert lo.shape == LuminousShape.HORIZONTAL_CYLINDER_ALONG
        assert lo.is_circular
        assert lo.is_3d

    def test_horizontal_elliptical_cylinder_along(self):
        """(-W, +L, -H) with W != H should be HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG."""
        lo = LuminousOpening(-0.1, 0.5, -0.2)
        assert lo.shape == LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_ALONG
        assert not lo.is_circular
        assert lo.is_3d

    def test_horizontal_cylinder_perpendicular(self):
        """(+W, -D, -D) should be HORIZONTAL_CYLINDER_PERPENDICULAR."""
        lo = LuminousOpening(0.5, -0.1, -0.1)
        assert lo.shape == LuminousShape.HORIZONTAL_CYLINDER_PERPENDICULAR
        assert lo.is_circular
        assert lo.is_3d

    def test_horizontal_elliptical_cylinder_perpendicular(self):
        """(+W, -L, -H) with L != H should be HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR."""
        lo = LuminousOpening(0.5, -0.1, -0.2)
        assert lo.shape == LuminousShape.HORIZONTAL_ELLIPTICAL_CYLINDER_PERPENDICULAR
        assert not lo.is_circular
        assert lo.is_3d

    def test_vertical_circle(self):
        """(-D, 0, -D) should be VERTICAL_CIRCLE."""
        lo = LuminousOpening(-0.1, 0, -0.1)
        assert lo.shape == LuminousShape.VERTICAL_CIRCLE
        assert lo.is_circular
        assert not lo.is_3d

    def test_vertical_ellipse(self):
        """(-W, 0, -H) with W != H should be VERTICAL_ELLIPSE."""
        lo = LuminousOpening(-0.1, 0, -0.2)
        assert lo.shape == LuminousShape.VERTICAL_ELLIPSE
        assert not lo.is_circular
        assert not lo.is_3d


class TestAreaCalculations:
    """Tests for area calculations."""

    def test_point_area(self):
        """Point should have zero area."""
        lo = LuminousOpening(0, 0, 0)
        assert lo.area() == 0.0

    def test_rectangular_area(self):
        """Rectangular area = W * L."""
        lo = LuminousOpening(0.1, 0.2, 0)  # 10cm x 20cm
        assert math.isclose(lo.area(), 0.02, rel_tol=1e-9)  # 0.02 m^2

    def test_rectangular_with_sides_opening_area(self):
        """Rectangular with sides opening area = W * L."""
        lo = LuminousOpening(0.1, 0.2, 0.05)
        assert math.isclose(lo.area("opening"), 0.02, rel_tol=1e-9)

    def test_rectangular_with_sides_total_area(self):
        """Rectangular with sides total area = 2*(WL + WH + LH)."""
        lo = LuminousOpening(0.1, 0.2, 0.05)
        expected = 2 * (0.1 * 0.2 + 0.1 * 0.05 + 0.2 * 0.05)
        assert math.isclose(lo.area("total"), expected, rel_tol=1e-9)

    def test_circular_area(self):
        """Circular area = pi * r^2."""
        lo = LuminousOpening(-0.2, -0.2, 0)  # 20cm diameter
        expected = math.pi * 0.1**2
        assert math.isclose(lo.area(), expected, rel_tol=1e-9)

    def test_ellipse_area(self):
        """Ellipse area = pi * a * b."""
        lo = LuminousOpening(-0.2, -0.4, 0)  # 20cm x 40cm
        expected = math.pi * 0.1 * 0.2
        assert math.isclose(lo.area(), expected, rel_tol=1e-9)

    def test_sphere_opening_area(self):
        """Sphere opening area = pi * r^2 (projected circle)."""
        lo = LuminousOpening(-0.2, -0.2, -0.2)  # 20cm diameter
        expected = math.pi * 0.1**2
        assert math.isclose(lo.area("opening"), expected, rel_tol=1e-9)

    def test_sphere_total_area(self):
        """Sphere total area = 4 * pi * r^2."""
        lo = LuminousOpening(-0.2, -0.2, -0.2)  # 20cm diameter
        expected = 4 * math.pi * 0.1**2
        assert math.isclose(lo.area("total"), expected, rel_tol=1e-9)

    def test_vertical_cylinder_opening_area(self):
        """Vertical cylinder opening area = pi * r^2."""
        lo = LuminousOpening(-0.2, -0.2, 0.5)  # 20cm diameter, 50cm height
        expected = math.pi * 0.1**2
        assert math.isclose(lo.area("opening"), expected, rel_tol=1e-9)

    def test_vertical_cylinder_total_area(self):
        """Vertical cylinder total area = 2*pi*r^2 + 2*pi*r*h."""
        lo = LuminousOpening(-0.2, -0.2, 0.5)  # 20cm diameter, 50cm height
        r = 0.1
        h = 0.5
        expected = 2 * math.pi * r * r + 2 * math.pi * r * h
        assert math.isclose(lo.area("total"), expected, rel_tol=1e-9)


class TestVolumeCalculations:
    """Tests for volume calculations."""

    def test_point_volume(self):
        """Point should have zero volume."""
        lo = LuminousOpening(0, 0, 0)
        assert lo.volume() == 0.0

    def test_rectangular_volume(self):
        """2D rectangular should have zero volume."""
        lo = LuminousOpening(0.1, 0.2, 0)
        assert lo.volume() == 0.0

    def test_circular_volume(self):
        """2D circular should have zero volume."""
        lo = LuminousOpening(-0.1, -0.1, 0)
        assert lo.volume() == 0.0

    def test_rectangular_with_sides_volume(self):
        """Rectangular with sides volume = W * L * H."""
        lo = LuminousOpening(0.1, 0.2, 0.05)
        expected = 0.1 * 0.2 * 0.05
        assert math.isclose(lo.volume(), expected, rel_tol=1e-9)

    def test_vertical_cylinder_volume(self):
        """Vertical cylinder volume = pi * r^2 * h."""
        lo = LuminousOpening(-0.2, -0.2, 0.5)  # 20cm diameter, 50cm height
        expected = math.pi * 0.1**2 * 0.5
        assert math.isclose(lo.volume(), expected, rel_tol=1e-9)

    def test_vertical_elliptical_cylinder_volume(self):
        """Vertical elliptical cylinder volume = pi * a * b * h."""
        lo = LuminousOpening(-0.2, -0.4, 0.5)
        expected = math.pi * 0.1 * 0.2 * 0.5
        assert math.isclose(lo.volume(), expected, rel_tol=1e-9)

    def test_sphere_volume(self):
        """Sphere volume = (4/3) * pi * r^3."""
        lo = LuminousOpening(-0.2, -0.2, -0.2)  # 20cm diameter
        expected = (4 / 3) * math.pi * 0.1**3
        assert math.isclose(lo.volume(), expected, rel_tol=1e-9)

    def test_ellipsoidal_spheroid_volume(self):
        """Ellipsoid volume = (4/3) * pi * a * b * c."""
        lo = LuminousOpening(-0.2, -0.4, -0.3)
        expected = (4 / 3) * math.pi * 0.1 * 0.2 * 0.15
        assert math.isclose(lo.volume(), expected, rel_tol=1e-9)

    def test_horizontal_cylinder_along_volume(self):
        """Horizontal cylinder along volume = pi * r^2 * length."""
        lo = LuminousOpening(-0.2, 0.5, -0.2)
        expected = math.pi * 0.1**2 * 0.5
        assert math.isclose(lo.volume(), expected, rel_tol=1e-9)


class TestPerimeterCalculations:
    """Tests for perimeter calculations."""

    def test_point_perimeter(self):
        """Point should have zero perimeter."""
        lo = LuminousOpening(0, 0, 0)
        assert lo.perimeter() == 0.0

    def test_rectangular_perimeter(self):
        """Rectangular perimeter = 2 * (W + L)."""
        lo = LuminousOpening(0.1, 0.2, 0)
        expected = 2 * (0.1 + 0.2)
        assert math.isclose(lo.perimeter(), expected, rel_tol=1e-9)

    def test_circular_perimeter(self):
        """Circular perimeter = pi * diameter."""
        lo = LuminousOpening(-0.2, -0.2, 0)  # 20cm diameter
        expected = math.pi * 0.2
        assert math.isclose(lo.perimeter(), expected, rel_tol=1e-9)


class TestEffectiveDiameter:
    """Tests for effective diameter calculation."""

    def test_point_effective_diameter(self):
        """Point should have zero effective diameter."""
        lo = LuminousOpening(0, 0, 0)
        assert lo.effective_diameter == 0.0

    def test_circular_effective_diameter(self):
        """Circular effective diameter should equal actual diameter."""
        lo = LuminousOpening(-0.2, -0.2, 0)  # 20cm diameter
        assert math.isclose(lo.effective_diameter, 0.2, rel_tol=1e-9)

    def test_rectangular_effective_diameter(self):
        """Rectangular effective diameter = 2*sqrt(area/pi)."""
        lo = LuminousOpening(0.1, 0.2, 0)  # 10cm x 20cm
        area = 0.02
        expected = 2 * math.sqrt(area / math.pi)
        assert math.isclose(lo.effective_diameter, expected, rel_tol=1e-9)


class TestUnitConversion:
    """Tests for unit conversion methods."""

    def test_area_in_meters(self):
        """Area in meters should match base area."""
        lo = LuminousOpening(0.1, 0.2, 0)
        assert math.isclose(lo.area_in("meters"), lo.area(), rel_tol=1e-9)

    def test_area_in_feet(self):
        """Area in feet should convert correctly."""
        lo = LuminousOpening(0.3048, 0.3048, 0)  # 1ft x 1ft in meters
        assert math.isclose(lo.area_in("feet"), 1.0, rel_tol=1e-6)

    def test_area_in_inches(self):
        """Area in inches should convert correctly."""
        lo = LuminousOpening(0.0254, 0.0254, 0)  # 1in x 1in in meters
        assert math.isclose(lo.area_in("inches"), 1.0, rel_tol=1e-6)

    def test_area_in_cm(self):
        """Area in cm should convert correctly."""
        lo = LuminousOpening(0.1, 0.2, 0)  # 10cm x 20cm
        expected = 10 * 20  # 200 cm^2
        assert math.isclose(lo.area_in("cm"), expected, rel_tol=1e-6)

    def test_area_in_invalid_units(self):
        """Invalid units should raise ValueError."""
        lo = LuminousOpening(0.1, 0.2, 0)
        with pytest.raises(ValueError, match="Unknown units"):
            lo.area_in("parsecs")

    def test_volume_in_meters(self):
        """Volume in meters should match base volume."""
        lo = LuminousOpening(0.1, 0.2, 0.05)
        assert math.isclose(lo.volume_in("meters"), lo.volume(), rel_tol=1e-9)

    def test_volume_in_cm(self):
        """Volume in cm should convert correctly."""
        lo = LuminousOpening(0.1, 0.2, 0.05)  # 10cm x 20cm x 5cm
        expected = 10 * 20 * 5  # 1000 cm^3
        assert math.isclose(lo.volume_in("cm"), expected, rel_tol=1e-6)

    def test_dimensions_in_meters(self):
        """Dimensions in meters should match original."""
        lo = LuminousOpening(0.1, -0.2, 0.05)
        w, l, h = lo.dimensions_in("meters")
        assert math.isclose(w, 0.1, rel_tol=1e-9)
        assert math.isclose(l, -0.2, rel_tol=1e-9)
        assert math.isclose(h, 0.05, rel_tol=1e-9)

    def test_dimensions_in_cm(self):
        """Dimensions in cm should convert correctly."""
        lo = LuminousOpening(0.1, -0.2, 0.05)  # meters
        w, l, h = lo.dimensions_in("cm")
        assert math.isclose(w, 10, rel_tol=1e-6)
        assert math.isclose(l, -20, rel_tol=1e-6)  # sign preserved
        assert math.isclose(h, 5, rel_tol=1e-6)

    def test_dimensions_preserve_sign(self):
        """Dimensions should preserve sign for shape encoding."""
        lo = LuminousOpening(-0.1, -0.1, 0)
        w, l, h = lo.dimensions_in("cm")
        assert w < 0  # Sign preserved
        assert l < 0  # Sign preserved


class TestFromHeader:
    """Tests for creating LuminousOpening from IES header values."""

    def test_from_header_meters(self):
        """From header with meters units should not convert."""
        lo = LuminousOpening.from_header(0.1, 0.2, 0.0, units=2)
        assert math.isclose(lo.width, 0.1, rel_tol=1e-9)
        assert math.isclose(lo.length, 0.2, rel_tol=1e-9)
        assert math.isclose(lo.height, 0.0, rel_tol=1e-9)

    def test_from_header_feet(self):
        """From header with feet units should convert to meters."""
        lo = LuminousOpening.from_header(1.0, 2.0, 0.0, units=1)
        assert math.isclose(lo.width, 0.3048, rel_tol=1e-6)
        assert math.isclose(lo.length, 0.6096, rel_tol=1e-6)
        assert math.isclose(lo.height, 0.0, rel_tol=1e-9)


class TestImmutability:
    """Tests that LuminousOpening is immutable."""

    def test_frozen(self):
        """LuminousOpening should be frozen (immutable)."""
        lo = LuminousOpening(0.1, 0.2, 0.0)
        with pytest.raises(Exception):  # FrozenInstanceError
            lo.width = 0.5


class TestRepr:
    """Tests for string representation."""

    def test_repr_contains_shape(self):
        """Repr should include shape name."""
        lo = LuminousOpening(-0.1, -0.1, 0)
        repr_str = repr(lo)
        assert "CIRCULAR" in repr_str
        assert "width" in repr_str
        assert "length" in repr_str
        assert "height" in repr_str


class TestIESHeaderIntegration:
    """Tests for IESHeader.luminous_opening property."""

    def test_header_luminous_opening(self, sample_path):
        """IESHeader should have luminous_opening property."""
        ies = IESFile.read(sample_path / "sample_A.ies")
        lo = ies.header.luminous_opening
        assert isinstance(lo, LuminousOpening)

    def test_header_luminous_opening_shape(self, sample_path):
        """luminous_opening should detect correct shape."""
        ies = IESFile.read(sample_path / "sample_A.ies")
        lo = ies.header.luminous_opening
        # Shape depends on actual file dimensions
        assert isinstance(lo.shape, LuminousShape)


class TestIESFileIntegration:
    """Tests for IESFile geometry integration."""

    def test_iesfile_luminous_opening(self, sample_path):
        """IESFile should have luminous_opening property."""
        ies = IESFile.read(sample_path / "sample_A.ies")
        lo = ies.luminous_opening
        assert isinstance(lo, LuminousOpening)

    def test_iesfile_lamp_area(self, sample_path):
        """IESFile should have lamp_area method."""
        ies = IESFile.read(sample_path / "sample_A.ies")
        area_m = ies.lamp_area("meters")
        area_cm = ies.lamp_area("cm")
        # cm^2 should be 10000x m^2
        assert math.isclose(area_cm, area_m * 10000, rel_tol=1e-6)

    def test_iesfile_lamp_area_default_meters(self, sample_path):
        """lamp_area default units should be meters."""
        ies = IESFile.read(sample_path / "sample_A.ies")
        area_default = ies.lamp_area()
        area_m = ies.lamp_area("meters")
        assert math.isclose(area_default, area_m, rel_tol=1e-9)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_small_dimensions(self):
        """Very small dimensions should still work."""
        lo = LuminousOpening(1e-9, 1e-9, 0)
        assert lo.shape == LuminousShape.RECTANGULAR
        assert lo.area() > 0

    def test_large_dimensions(self):
        """Large dimensions should still work."""
        lo = LuminousOpening(100.0, 100.0, 0)
        assert lo.shape == LuminousShape.RECTANGULAR
        assert math.isclose(lo.area(), 10000, rel_tol=1e-9)

    def test_near_zero_treated_as_zero(self):
        """Dimensions exactly zero should be detected."""
        lo = LuminousOpening(0.0, 0.0, 0.0)
        assert lo.shape == LuminousShape.POINT

    def test_circular_vs_ellipse_precision(self):
        """Very close but unequal values should be ellipse."""
        lo = LuminousOpening(-0.1, -0.100001, 0)
        # Should be ELLIPSE since values are not exactly equal
        assert lo.shape == LuminousShape.ELLIPSE

    def test_circular_exact_match(self):
        """Exactly equal values should be circular."""
        lo = LuminousOpening(-0.1, -0.1, 0)
        assert lo.shape == LuminousShape.CIRCULAR
