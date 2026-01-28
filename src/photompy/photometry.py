from dataclasses import dataclass, field
from enum import IntEnum, Enum
import numpy as np
import hashlib
from ._calculate import compute_frustrum_area
from ._plot import plot_polar, plot_cartesian
from .exceptions import IESDataError


class PhotometricType(IntEnum):
    C = 1
    B = 2
    A = 3


class LampSymmetry(Enum):
    NONE = "none"
    HALF = "half"
    QUAD = "quad"
    AXIAL = "axial"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BeamAngleResult:
    """Result of beam angle calculation."""
    angles: dict[float, float]  # phi -> beam angle mapping
    threshold: float
    min_angle: float
    max_angle: float
    mean_angle: float

    @property
    def angle(self) -> float:
        """Representative beam angle (minimum across all planes)."""
        return self.min_angle

    @property
    def is_asymmetric(self) -> bool:
        """True if beam varies more than 5% across phi planes."""
        if self.mean_angle == 0:
            return False
        return (self.max_angle - self.min_angle) / self.mean_angle > 0.05


@dataclass(slots=True)
class Photometry:
    thetas: np.ndarray
    phis: np.ndarray
    values: np.ndarray
    photometric_type: PhotometricType
    symmetry: LampSymmetry = field(init=False)

    _cache: dict = field(
        default_factory=dict,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self):
        if self.values.shape != (len(self.phis), len(self.thetas)):
            raise IESDataError("values shape mismatch")
        self.symmetry = self._infer_symmetry()

    def __eq__(self, other):
        if not isinstance(other, Photometry):
            return NotImplemented

        if self.photometric_type != other.photometric_type:
            return False

        if self.symmetry != other.symmetry:
            return False

        if not np.array_equal(self.thetas, other.thetas):
            return False
        if not np.array_equal(self.phis, other.phis):
            return False
        if not np.array_equal(self.values, other.values):
            return False

        return True

    def max(self):
        """maximum value of photometry values"""
        return self.values.max()

    def total(self):
        """convenience alias for total_optical_power"""
        return self.total_optical_power()

    def center(self):
        """center irradiance"""
        return self.get_intensity(theta=0, phi=0)

    def total_optical_power(self) -> float:
        """compute the total optical power"""
        thetastep = self.thetas[1] - self.thetas[0]
        thetasums = self.values.sum(axis=0) / len(self.phis)
        thetas1 = np.maximum(0, self.thetas - thetastep / 2)  # Avoid negative angles
        thetas2 = self.thetas + thetastep / 2
        areas = compute_frustrum_area(thetas1, thetas2)
        total_power = (thetasums * areas).sum()
        return total_power

    def scale_to_max(self, max_val):
        """scale the photometry to a maximum value"""
        if max_val <= 0:
            raise ValueError("scaling value must be positive")
        self.values = self.values * max_val / self.values.max()
        for phot in self._cache.values():
            if isinstance(phot, Photometry):
                phot.values = phot.values * max_val / phot.values.max()
        return self.values

    def scale_to_total(self, total_power):
        """scale the photometry to a total optical power"""
        if total_power <= 0:
            raise ValueError("scaling value must be positive")
        self.values = self.values * total_power / self.total()
        for phot in self._cache.values():
            if isinstance(phot, Photometry):
                phot.values = phot.values * total_power / phot.total()
        return self.values

    def scale_to_center(self, center_val):
        """scale the photometry to a center value"""
        if center_val <= 0:
            raise ValueError("scaling value must be positive")
        self.values = self.values * center_val / self.get_intensity(0, 0)
        for phot in self._cache.values():
            if isinstance(phot, Photometry):
                phot.values = phot.values * center_val / phot.get_intensity(0, 0)
        return self.values

    def scale(self, scale_val):
        """scale the photometry by the given value"""
        if scale_val <= 0:
            raise ValueError("scaling value must be positive")
        self.values = self.values * scale_val
        for phot in self._cache.values():
            if isinstance(phot, Photometry):
                phot.values = phot.values * scale_val
        return self.values

    def get_intensity(self, theta, phi):
        """
        Determine arbitrary intensity value anywhere on the photometric solid.

        For Type C: theta is 0-180 (nadir to zenith), phi is 0-360 (azimuth)
        For Type B/A: theta is -90 to 90 (vertical), phi is -90 to 90 (horizontal)

        theta : array-like
            Vertical angle(s) of interest
        phi : array-like
            Horizontal/azimuthal angle(s) of interest

        Returns:
        float or ndarray
            Interpolated intensity value(s)
        """

        thetamap = self.thetas
        phimap = self.phis
        valuemap = self.values

        try:
            theta, phi = np.broadcast_arrays(theta, phi)
        except ValueError as e:
            raise ValueError("theta and phi shapes are not broadcast-compatible") from e

        if theta.shape != phi.shape:
            raise ValueError("theta and phi must be of same length")

        # Range checks depend on photometric type
        theta_min, theta_max = thetamap[0], thetamap[-1]
        phi_min, phi_max = phimap[0], phimap[-1]

        if np.any(theta < theta_min) or np.any(theta > theta_max):
            raise ValueError(
                f"Theta values must be between {theta_min} and {theta_max} degrees"
            )

        # Normalize phi for Type C (wraps around 360)
        if self.photometric_type == PhotometricType.C:
            phi = np.mod(phi, 360)

        # Finding closest indices for phi and theta
        phi_indices = np.searchsorted(phimap, phi, side="left")
        theta_indices = np.searchsorted(thetamap, theta, side="left")

        # Handle boundary conditions for interpolation
        phi_indices = np.clip(phi_indices, 1, len(phimap) - 1)
        theta_indices = np.clip(theta_indices, 1, len(thetamap) - 1)

        # Compute interpolation weights (with division-by-zero protection)
        phi_denom = phimap[phi_indices] - phimap[phi_indices - 1]
        theta_denom = thetamap[theta_indices] - thetamap[theta_indices - 1]
        phi_weights = np.divide(
            phi - phimap[phi_indices - 1], phi_denom,
            out=np.zeros_like(phi, dtype=float), where=phi_denom != 0
        )
        theta_weights = np.divide(
            theta - thetamap[theta_indices - 1], theta_denom,
            out=np.zeros_like(theta, dtype=float), where=theta_denom != 0
        )

        # Interpolate values
        val1 = (
            valuemap[phi_indices - 1, theta_indices - 1] * (1 - phi_weights)
            + valuemap[phi_indices, theta_indices - 1] * phi_weights
        )
        val2 = (
            valuemap[phi_indices - 1, theta_indices] * (1 - phi_weights)
            + valuemap[phi_indices, theta_indices] * phi_weights
        )
        final_val = val1 * (1 - theta_weights) + val2 * theta_weights

        return final_val

    def expanded(self):
        """return a photometry with fully mirrored values"""
        try:
            exp = self._cache["expanded"]
        except KeyError:
            exp = self._expand_angles()  # compute expansion
            self._cache["expanded"] = exp
        return exp

    def plot_polar(self, **kwargs):
        exp = self.expanded()
        return plot_polar(thetas=exp.thetas, phis=exp.phis, values=exp.values, **kwargs)

    def plot_cartesian(self, **kwargs):
        exp = self.expanded()
        return plot_cartesian(
            thetas=exp.thetas, phis=exp.phis, values=exp.values, **kwargs
        )

    @staticmethod
    def to_cartesian(theta, phi, r):
        """
        convert from degrees polar to cartesian coordinates
        """
        theta_rad = np.radians(theta)
        phi_rad = np.radians(phi)
        x = r * np.sin(theta_rad) * np.sin(phi_rad)
        y = r * np.sin(theta_rad) * np.cos(phi_rad)
        z = r * np.cos(theta_rad)

        return np.array((x, y, z))

    @property
    def coords(self):
        try:
            return self._cache["coords"]
        except KeyError:
            c = self._make_coords()
            self._cache["coords"] = c
            return c

    @property
    def photometric_coords(self):
        try:
            return self._cache["pcoords"]
        except KeyError:
            pc = self._make_photometric_coords()
            self._cache["pcoords"] = pc
            return pc

    def interpolated(self, num_thetas=181, num_phis=361):
        """Return a fully expanded and interpolated photometry.

        Creates a new Photometry with evenly-spaced angles and bilinearly
        interpolated intensity values. The result is cached for efficiency.

        num_thetas : int, default=181
            Number of theta (vertical) angles in result (0-180 range).
        num_phis : int, default=361
            Number of phi (horizontal) angles in result (0-360 range).

        Returns:
        Photometry
            New photometry with interpolated values.
        """
        key = ("interpolated", num_thetas, num_phis)
        try:
            interp = self._cache[key]
        except KeyError:
            interp = self._interpolate_angles(num_thetas, num_phis)
            self._cache[key] = interp
        return interp

    def to_fingerprint(self) -> bytes:
        """hash the photometry"""
        arr = np.concatenate([self.thetas,self.phis,self.values.flatten()])
        return hashlib.sha1(arr.tobytes()).digest()

    def get_beam_angle(self, threshold: float = 0.5, num_points: int = 1000) -> BeamAngleResult:
        """
        Calculate beam angle from photometry data.

        The beam angle is the full cone angle where intensity drops to a
        threshold percentage of maximum intensity.

        threshold : float, default=0.5
            Fraction of maximum intensity for beam angle (0.5 = 50% = beam angle,
            0.1 = 10% = field angle).
        num_points : int, default=1000
            Number of points to sample for interpolation.

        Returns:
        BeamAngleResult
            Result containing beam angles for each phi plane and statistics.
        """
        cache_key = ("beam_angle", threshold, num_points)
        try:
            return self._cache[cache_key]
        except KeyError:
            pass

        if self.photometric_type == PhotometricType.C:
            result = self._beam_angle_type_c(threshold, num_points)
        else:
            result = self._beam_angle_type_b_a(threshold, num_points)

        self._cache[cache_key] = result
        return result

    @property
    def beam_angle(self) -> float:
        """Beam angle at 50% intensity threshold."""
        return self.get_beam_angle(threshold=0.5).angle

    @property
    def field_angle(self) -> float:
        """Field angle at 10% intensity threshold."""
        return self.get_beam_angle(threshold=0.1).angle

    # ------------------ Internals ------------------

    def _infer_symmetry(self):
        """
        Infer lamp symmetry from horizontal angle range.

        Type C: phis are horizontal angles (0-360 or subset)
        Type B: phis are horizontal angles H (-90 to 90 or 0 to 90)
        Type A: phis are horizontal angles (similar to Type B, rotated 90)
        """

        if self.photometric_type == PhotometricType.C:
            if not np.isclose(self.phis[0], 0):
                raise IESDataError("IES file photometry is malformed")

            span = self.phis[-1]
            if np.isclose(span, 360):
                return LampSymmetry.NONE
            if np.isclose(span, 180):
                return LampSymmetry.HALF
            if np.isclose(span, 90):
                return LampSymmetry.QUAD
            if np.isclose(span, 0):
                return LampSymmetry.AXIAL
            return LampSymmetry.UNKNOWN

        elif self.photometric_type == PhotometricType.B:
            # Type B: H angles from -90 to 90 or 0 to 90
            first_h = self.phis[0]
            last_h = self.phis[-1]

            if np.isclose(first_h, 0) and np.isclose(last_h, 90):
                return LampSymmetry.QUAD  # Quadrant symmetric
            elif np.isclose(first_h, -90) and np.isclose(last_h, 90):
                return LampSymmetry.HALF  # Only half symmetric (left-right)
            elif np.isclose(first_h, 0) and np.isclose(last_h, 0):
                return LampSymmetry.AXIAL  # Single plane
            return LampSymmetry.UNKNOWN

        elif self.photometric_type == PhotometricType.A:
            # Type A: Similar to Type B
            first_h = self.phis[0]
            last_h = self.phis[-1]

            if np.isclose(first_h, 0) and np.isclose(last_h, 90):
                return LampSymmetry.QUAD
            elif np.isclose(first_h, -90) and np.isclose(last_h, 90):
                return LampSymmetry.HALF
            elif np.isclose(first_h, 0) and np.isclose(last_h, 0):
                return LampSymmetry.AXIAL
            return LampSymmetry.UNKNOWN

        return LampSymmetry.UNKNOWN

    def _expand_angles(self):
        """return a photometry with fully mirrored values"""
        if self.photometric_type == PhotometricType.C:
            return self._expand_angles_type_c()
        elif self.photometric_type == PhotometricType.B:
            return self._expand_angles_type_b()
        elif self.photometric_type == PhotometricType.A:
            return self._expand_angles_type_a()
        else:
            raise NotImplementedError(
                f"Photometric type {self.photometric_type} is not supported"
            )

    def _expand_angles_type_c(self):
        """Expand Type C photometry based on symmetry."""
        if self.symmetry == LampSymmetry.AXIAL:  # C0
            phis = np.arange(0, 360)
            values = np.tile(self.values, (360, 1))  # repeat rows for each phi
        elif self.symmetry == LampSymmetry.QUAD:  # C90
            phis1 = self.phis
            phis2 = phis1[1:] + 90
            phis3 = phis1[1:] + 180
            phis4 = phis1[1:] + 270
            phis = np.concatenate((phis1, phis2, phis3, phis4))

            vals1 = self.values[:-1]
            vals2 = np.flip(self.values, axis=0)
            vals3 = np.concatenate((vals1, vals2))
            vals4 = np.flip(vals3[:-1], axis=0)
            values = np.concatenate((vals3, vals4))

        elif self.symmetry == LampSymmetry.HALF:  # C180
            phis1 = self.phis
            phis2 = phis1[1:] + 180
            phis = np.concatenate((phis1, phis2))
            vals1 = self.values[:-1]
            vals2 = np.flip(self.values, axis=0)
            values = np.concatenate((vals1, vals2))
        elif self.symmetry == LampSymmetry.NONE:
            phis = self.phis
            values = self.values
        else:
            raise NotImplementedError(
                f"Lamp symmetry {self.symmetry} is not supported for Type C"
            )

        # fill in thetas
        if np.isclose(self.thetas[-1], 90):
            val = self.thetas[-1]
            step = self.thetas[-1] - self.thetas[-2]
            extrathetas = []
            while val < 180:
                val = val + step
                extrathetas.append(val)
            extravals = np.zeros((len(phis), len(extrathetas)))

            thetas = np.concatenate((self.thetas, extrathetas))
            values = np.concatenate((values.T, extravals.T)).T

        else:
            thetas = self.thetas

        return Photometry(
            thetas=thetas,
            phis=phis,
            values=values,
            photometric_type=self.photometric_type,
        )

    def _expand_angles_type_b(self):
        """
        Expand Type B photometry based on symmetry.

        Type B coordinate system:
        - Vertical angles (V): stored in thetas, range -90 to 90 (or 0 to 90)
        - Horizontal angles (H): stored in phis, range -90 to 90 (or 0 to 90)

        For expansion, we mirror to get full coverage.
        """
        thetas = self.thetas.copy()
        values = self.values.copy()

        # Expand vertical angles (thetas) to -90 to 90 if needed
        if np.isclose(thetas[0], 0) and np.isclose(thetas[-1], 90):
            # V goes from 0 to 90, mirror to -90 to 90
            neg_thetas = -np.flip(thetas[1:])  # -90 to -step (excluding 0)
            thetas = np.concatenate((neg_thetas, thetas))
            # Mirror values: negative V angles have same values as positive
            neg_values = np.flip(values, axis=1)[:, 1:]
            values = np.concatenate((neg_values, values), axis=1)

        # Expand horizontal angles (phis)
        if self.symmetry == LampSymmetry.QUAD:
            # H goes from 0 to 90, mirror to -90 to 90
            phis1 = self.phis
            phis2 = -np.flip(phis1[1:])  # -90 to -step (excluding 0)
            phis = np.concatenate((phis2, phis1))

            vals1 = values
            vals2 = np.flip(values[1:], axis=0)
            values = np.concatenate((vals2, vals1))

        elif self.symmetry == LampSymmetry.HALF:
            # H already goes from -90 to 90
            phis = self.phis

        elif self.symmetry == LampSymmetry.AXIAL:
            # Single plane: expand to full H range
            phis = np.linspace(-90, 90, 181)
            values = np.tile(values, (len(phis), 1))

        else:
            raise NotImplementedError(
                f"Lamp symmetry {self.symmetry} is not supported for Type B"
            )

        return Photometry(
            thetas=thetas,
            phis=phis,
            values=values,
            photometric_type=self.photometric_type,
        )

    def _expand_angles_type_a(self):
        """
        Expand Type A photometry based on symmetry.

        Type A is similar to Type B but rotated 90 degrees.
        Uses the same expansion logic as Type B.
        """
        thetas = self.thetas.copy()
        values = self.values.copy()

        # Expand vertical angles (thetas) to -90 to 90 if needed
        if np.isclose(thetas[0], 0) and np.isclose(thetas[-1], 90):
            neg_thetas = -np.flip(thetas[1:])
            thetas = np.concatenate((neg_thetas, thetas))
            neg_values = np.flip(values, axis=1)[:, 1:]
            values = np.concatenate((neg_values, values), axis=1)

        # Expand horizontal angles (phis)
        if self.symmetry == LampSymmetry.QUAD:
            phis1 = self.phis
            phis2 = -np.flip(phis1[1:])
            phis = np.concatenate((phis2, phis1))

            vals1 = values
            vals2 = np.flip(values[1:], axis=0)
            values = np.concatenate((vals2, vals1))

        elif self.symmetry == LampSymmetry.HALF:
            phis = self.phis

        elif self.symmetry == LampSymmetry.AXIAL:
            phis = np.linspace(-90, 90, 181)
            values = np.tile(values, (len(phis), 1))

        else:
            raise NotImplementedError(
                f"Lamp symmetry {self.symmetry} is not supported for Type A"
            )

        return Photometry(
            thetas=thetas,
            phis=phis,
            values=values,
            photometric_type=self.photometric_type,
        )

    def _make_coords(self):
        """generate cartesian coordinates for plotting purposes"""
        exp = self.expanded()
        tgrid, pgrid = np.meshgrid(exp.thetas, exp.phis)
        tflat, pflat = tgrid.flatten(), pgrid.flatten()
        x, y, z = self.to_cartesian(tflat, pflat, 1)
        return np.array([x, y, -z]).T

    def _make_photometric_coords(self):
        """generate value-scaled cartesian coordinates for plotting purposes"""
        exp = self.expanded()
        tgrid, pgrid = np.meshgrid(exp.thetas, exp.phis)
        tflat, pflat = tgrid.flatten(), pgrid.flatten()
        xp, yp, zp = exp.to_cartesian(tflat, pflat, exp.values.flatten())
        return np.array([xp, yp, -zp]).T

    def _interpolate_angles(self, num_thetas=181, num_phis=361):
        """
        Return a photometry with evenly-spaced interpolated angles.

        For Type C: theta 0-180, phi 0-360
        For Type B/A: theta -90 to 90, phi -90 to 90
        """

        expanded = self.expanded()

        # Use appropriate ranges based on photometric type
        if self.photometric_type == PhotometricType.C:
            new_thetas = np.linspace(0, 180, num_thetas)
            new_phis = np.linspace(0, 360, num_phis)
        else:
            # Type A and Type B use -90 to 90 for both angles
            new_thetas = np.linspace(-90, 90, num_thetas)
            new_phis = np.linspace(-90, 90, num_phis)

        tgrid, pgrid = np.meshgrid(new_thetas, new_phis)
        tflat, pflat = tgrid.flatten(), pgrid.flatten()

        intensity = expanded.get_intensity(tflat, pflat)
        newvalues = intensity.reshape(num_phis, num_thetas)

        return Photometry(
            thetas=new_thetas,
            phis=new_phis,
            values=newvalues,
            photometric_type=expanded.photometric_type,
        )

    def _beam_angle_type_c(self, threshold: float, num_points: int) -> BeamAngleResult:
        """Calculate beam angle for Type C (nadir-based) photometry."""
        max_intensity = self.max()
        target_intensity = max_intensity * threshold

        expanded = self.expanded()
        angles = {}

        for phi in expanded.phis:
            half_angle = self._find_half_angle(
                expanded, phi, target_intensity, num_points, theta_start=0, theta_end=180
            )
            if half_angle is not None:
                angles[float(phi)] = 2 * half_angle  # Full cone angle

        if not angles:
            return BeamAngleResult(
                angles={},
                threshold=threshold,
                min_angle=0.0,
                max_angle=0.0,
                mean_angle=0.0,
            )

        angle_values = list(angles.values())
        return BeamAngleResult(
            angles=angles,
            threshold=threshold,
            min_angle=min(angle_values),
            max_angle=max(angle_values),
            mean_angle=sum(angle_values) / len(angle_values),
        )

    def _beam_angle_type_b_a(self, threshold: float, num_points: int) -> BeamAngleResult:
        """Calculate beam angle for Type B/A photometry."""
        max_intensity = self.max()
        target_intensity = max_intensity * threshold

        expanded = self.expanded()
        angles = {}

        for phi in expanded.phis:
            # For Type B/A, we measure from center (theta=0) outward in both directions
            half_angle_pos = self._find_half_angle(
                expanded, phi, target_intensity, num_points, theta_start=0, theta_end=90
            )
            half_angle_neg = self._find_half_angle(
                expanded, phi, target_intensity, num_points, theta_start=0, theta_end=-90
            )

            if half_angle_pos is not None and half_angle_neg is not None:
                angles[float(phi)] = half_angle_pos + half_angle_neg
            elif half_angle_pos is not None:
                angles[float(phi)] = 2 * half_angle_pos
            elif half_angle_neg is not None:
                angles[float(phi)] = 2 * half_angle_neg

        if not angles:
            return BeamAngleResult(
                angles={},
                threshold=threshold,
                min_angle=0.0,
                max_angle=0.0,
                mean_angle=0.0,
            )

        angle_values = list(angles.values())
        return BeamAngleResult(
            angles=angles,
            threshold=threshold,
            min_angle=min(angle_values),
            max_angle=max(angle_values),
            mean_angle=sum(angle_values) / len(angle_values),
        )

    def _find_half_angle(
        self,
        photometry: "Photometry",
        phi: float,
        target_intensity: float,
        num_points: int,
        theta_start: float,
        theta_end: float,
    ) -> float | None:
        """
        Find the angle where intensity crosses the target threshold.

        photometry : Photometry
            The photometry to sample from (typically expanded).
        phi : float
            The phi plane to search in.
        target_intensity : float
            The intensity threshold to find.
        num_points : int
            Number of points to sample.
        theta_start : float
            Starting theta angle (center of beam).
        theta_end : float
            Ending theta angle (edge of beam).

        Returns:
        float or None
            The half-angle where intensity drops below target, or None if not found.
        """
        thetas = np.linspace(theta_start, theta_end, num_points)
        phis = np.full(num_points, phi)
        intensities = photometry.get_intensity(thetas, phis)

        # Find first crossing point where intensity < target
        for i in range(1, len(intensities)):
            if intensities[i] < target_intensity <= intensities[i - 1]:
                # Linear interpolation to find exact crossing
                t0, t1 = thetas[i - 1], thetas[i]
                i0, i1 = intensities[i - 1], intensities[i]
                if i0 != i1:
                    crossing = t0 + (target_intensity - i0) * (t1 - t0) / (i1 - i0)
                else:
                    crossing = t0
                return abs(crossing - theta_start)

        return None
