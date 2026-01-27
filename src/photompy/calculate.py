import numpy as np
import pathlib
import os
from .read import verify_valdict


def total_optical_power(data, num_thetas=181, num_phis=361, distance=1):
    """
    calculate the total optical power of a lamp given an .ies file

    data: either an .ies filename to calculate from, or a pre-load value
        dictionary containing keys `phis`,`thetas`, and `values`
    num_thetas: number of vertical angles to interpolate between.
        Ignored if data is a dict.
    num_phis: number of horizontal angles to interpolate between
        Ignored if data is a dict.
    distance: lamp distance from sensor, in meters. Generally 1.
    """
    if isinstance(data, (str, pathlib.PosixPath)) and os.path.isfile(data):
        valdict = _load_interpdict(data, num_thetas, num_phis)
        result = _compute_total_power(valdict)
    elif isinstance(data, dict):
        verify_valdict(data)  # will raise errors if valdict is malformed
        result = _compute_total_power(data)
    else:
        raise ValueError("data must be either an .ies file or a dict object")
    return result


def _load_interpdict(filename, num_thetas, num_phis):
    """
    load a dictionary with interpolated values
    """
    from .ies import IESFile  # lazy import to avoid circular dependency
    ies_file = IESFile.read(filename)
    interp_phot = ies_file.photometry.interpolated(num_thetas, num_phis)
    return {
        "thetas": interp_phot.thetas,
        "phis": interp_phot.phis,
        "values": interp_phot.values,
    }


def _compute_total_power(valdict):
    """compute the total optical power"""
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


def compute_frustrum_area(theta1, theta2):
    a1 = 2 * np.pi * (1 - np.cos(np.radians(theta1)))  # r^2 = 1
    a2 = 2 * np.pi * (1 - np.cos(np.radians(theta2)))  # r^2 = 1
    return a2 - a1


def lamp_area(filename, units="meters", verbose=False):
    """
    return lamp area in units of m^2, ft^2 or in^2
    """

    if units.lower() not in ["meters", "feet", "inches"]:
        msg = "Argument units must be either `meters`,`feet`, or `inches"
        raise KeyError(msg)

    from .ies import IESFile  # lazy import to avoid circular dependency
    ies_file = IESFile.read(filename)
    header = ies_file.header
    if header.units == 1:
        # feet
        width_ft = header.width
        length_ft = header.length
        width_m = header.width * 0.3048
        length_m = header.length * 0.3048
    elif header.units == 2:
        # meters
        width_m = header.width
        length_m = header.length
        width_ft = header.width / 0.3048
        length_ft = header.length / 0.3048

    width_in, length_in = width_ft * 12, length_ft * 12

    if units.lower() == "feet":
        area = width_ft * length_ft
    elif units.lower() == "meters":
        area = width_m * length_m
    elif units.lower() == "inches":
        area = width_in * length_in
    if verbose:
        print("Area (cm2)", width_m * length_m * 100 * 100)
    return area
