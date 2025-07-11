from dataclasses import dataclass, field
from enum import IntEnum, Enum
import numpy as np
from .calculate import compute_frustrum_area
from .plot import plot_polar, plot_cartesian
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


@dataclass(slots=True)
class Photometry:
    thetas: np.ndarray
    phis: np.ndarray
    values: np.ndarray
    photometric_type: PhotometricType
    symmetry: LampSymmetry = field(init=False)
    strict: bool = True

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

    def max(self):
        """maximum value of photometry values"""
        return self.values.max()

    def total(self):
        """convenience alias for total_optical_power"""
        return self.total_optical_power()

    def center(self):
        """center irradiance"""
        return self.get_intensity(theta=0, phi=0)

    def expanded(self):
        """return a photometry with fully mirrored values"""
        try:
            exp = self._cache["expanded"]
        except KeyError:
            exp = self._expand_angles()  # compute expansion
            self._cache["expanded"] = exp
        return exp

    def interpolated(self, num_thetas=181, num_phis=361):
        """return a fully mirrored photometry with"""

        key = ("interpolated", num_thetas, num_phis)
        try:
            interp = self._cache[key]
        except KeyError:
            interp = self._interpolate_angles(num_thetas, num_phis)
            self._cache[key] = interp
        return interp

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
        self.values = self.values * max_val / self.values.max()
        for phot in self._cache.values():
            phot.values = phot.values * max_val / phot.values.max()
        return self.values

    def scale_to_total(self, total_power):
        """scale the photometry to a total optical power"""
        self.values = self.values * total_power / self.total()
        for phot in self._cache.values():
            phot.values = phot.values * total_power / phot.total()
        return self.values

    def scale_to_center(self, center_val):
        """scale the photometry to a center value"""
        self.values = self.values * center_val / self.get_intensity(0, 0)
        for phot in self._cache.values():
            phot.values = phot.values * center_val / phot.get_intensity(0, 0)
        return self.values

    def scale(self, scale_val):
        """scale the photometry by the given value"""
        self.values = self.values * scale_val
        for phot in self._cache.values():
            phot.values = phot.values * scale_val
        return self.values

    def get_intensity(self, theta, phi):
        """
        determine arbitrary intensity value anywhere on unit sphere

        theta: arraylike of vertical angle value of interest
        phi: arraylike of horizontal/azimuthal angle value of interest
        """

        thetamap = self.thetas
        phimap = self.phis
        valuemap = self.values

        try:
            theta, phi = np.broadcast_arrays(theta, phi)
        except ValueError as e:
            raise ValueError("theta and phi shapes are not broadcast-compatible") from e

        # Range checks for theta and phi
        if np.any(theta < 0) or np.any(theta > 180):
            raise ValueError("Theta values must be between 0 and 180 degrees")
        if theta.shape != phi.shape:
            raise ValueError("theta and phi must be of same length")
        phi = np.mod(phi, 360)  # Normalize phi values

        # Finding closest indices for phi and theta
        phi_indices = np.searchsorted(phimap, phi, side="left")
        theta_indices = np.searchsorted(thetamap, theta, side="left")

        # Handle boundary conditions for interpolation
        phi_indices = np.clip(phi_indices, 1, len(phimap) - 1)
        theta_indices = np.clip(theta_indices, 1, len(thetamap) - 1)

        # Compute interpolation weights
        phi_weights = (phi - phimap[phi_indices - 1]) / (
            phimap[phi_indices] - phimap[phi_indices - 1]
        )
        theta_weights = (theta - thetamap[theta_indices - 1]) / (
            thetamap[theta_indices] - thetamap[theta_indices - 1]
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

    # ------------------ Internals ------------------

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

    def _infer_symmetry(self):

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
        else:
            # A and B symmetries not yet supported
            return LampSymmetry.UNKNOWN

    def _expand_angles(self):
        """return a photometry with fully mirrored values"""
        if self.photometric_type == PhotometricType.C:
            if self.symmetry == LampSymmetry.AXIAL:  # C0
                phis = np.arange(0, 360)
                values = np.tile(self.values, 360).reshape(-1, 360)
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
                phis2 = phis[1:] + 180
                phis = np.concatenate((phis1, phis2))
                vals1 = self.values[:-1]
                vals2 = np.flip(self.values, axis=0)
                values = np.concatenate((vals1, vals2))
            elif self.symmetry == LampSymmetry.NONE:
                phis = self.phis
                values = self.values
            else:
                raise NotImplementedError(
                    f"Lamp symmetry {self.symmetry} is not supported"
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

        else:
            raise NotImplementedError("A and B photometries are not yet supported")

        return Photometry(
            thetas=thetas,
            phis=phis,
            values=values,
            photometric_type=self.photometric_type,
        )

    def _interpolate_angles(self, num_thetas=181, num_phis=361):
        """return a photometry fully filled out"""

        expanded = self.expanded()

        new_thetas = np.linspace(0, 180, num_thetas)
        new_phis = np.linspace(0, 360, num_phis)

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
