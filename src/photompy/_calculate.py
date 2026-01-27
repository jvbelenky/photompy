"""
Internal calculation helpers.

This module contains helper functions for photometric calculations.
These are internal implementation details, not part of the public API.
"""

import numpy as np


def compute_frustrum_area(theta1, theta2):
    """Compute the area of a spherical frustum between two theta angles."""
    a1 = 2 * np.pi * (1 - np.cos(np.radians(theta1)))  # r^2 = 1
    a2 = 2 * np.pi * (1 - np.cos(np.radians(theta2)))  # r^2 = 1
    return a2 - a1


def _load_interpdict(filename, num_thetas, num_phis):
    """Load a dictionary with interpolated values."""
    from .ies import IESFile  # lazy import to avoid circular dependency
    ies_file = IESFile.read(filename)
    interp_phot = ies_file.photometry.interpolated(num_thetas, num_phis)
    return {
        "thetas": interp_phot.thetas,
        "phis": interp_phot.phis,
        "values": interp_phot.values,
    }


def _compute_total_power(valdict):
    """Compute the total optical power from a valdict."""
    values = valdict["values"]
    phis = valdict["phis"]
    thetas = valdict["thetas"]

    thetastep = thetas[1] - thetas[0]
    thetasums = values.sum(axis=0) / len(phis)
    thetas1 = np.maximum(0, thetas - thetastep / 2)  # Avoid negative angles
    thetas2 = thetas + thetastep / 2
    areas = compute_frustrum_area(thetas1, thetas2)
    total_power = (thetasums * areas).sum()
    return total_power
