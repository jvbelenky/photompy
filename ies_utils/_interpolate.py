import bisect
import numpy as np
from ._read import verify_valdict


def interpolate(valdict, num_thetas=181, num_phis=361):

    """
    Fill in the values of an .ies value dictionary with interpolation
    Requires a lampdict with a `full vals` key
    """

    verify_valdict(valdict)
    newthetas = np.linspace(0, 180, num_thetas)
    newphis = np.linspace(0, 360, num_phis)

    tgrid, pgrid = np.meshgrid(newthetas, newphis)
    tflat, pflat = tgrid.flatten(), pgrid.flatten()

    intensity = [get_intensity(t, p, valdict) for t, p in zip(tflat, pflat)]
    newvalues = np.array(intensity).reshape(num_phis, num_thetas)

    newdict = {}
    newdict["thetas"] = newthetas
    newdict["phis"] = newphis
    newdict["values"] = newvalues

    return newdict


def get_intensity(theta, phi, valdict):
    """
    determine arbitrary intensity value anywhere on unit sphere

    theta: vertical angle value of interest
    phi: horizontal/azimuthal angle value of interest
    thetamap: existing theta value for which data is available
    phimap: existing phi vlaues for which data is available
    valuemap: array of shape (len(ph))

    """
    epsilon = np.finfo(np.float64).eps

    thetamap = valdict["thetas"]
    phimap = valdict["phis"]
    valuemap = valdict["values"]

    if theta < 0 or theta > 180:
        msg = "Theta must be >0 and <180 degrees, {} was passed".format(theta)
        raise ValueError(msg)

    if phi > 360 or phi < 0:
        phi = phi % 360

    # prevent div by zero errors
    if phi == 0:
        phi += epsilon
    if theta == 0:
        theta += epsilon

    phi_idx1, phi_idx2 = _find_closest(phimap, phi)
    theta_idx1, theta_idx2 = _find_closest(thetamap, theta)

    # Interpolate along phimap for both thetamap
    val1a = valuemap[phi_idx1][theta_idx1]
    val1b = valuemap[phi_idx2][theta_idx1]
    weight1 = (phi - phimap[phi_idx1]) / (phimap[phi_idx2] - phimap[phi_idx1])
    val1 = _linear_interpolate(val1a, val1b, weight1)

    val2a = valuemap[phi_idx1][theta_idx2]
    val2b = valuemap[phi_idx2][theta_idx2]
    val2 = _linear_interpolate(val2a, val2b, weight1)

    # Interpolate between the two results along thetamap
    denominator = thetamap[theta_idx2] - thetamap[theta_idx1]
    if denominator == 0:
        denominator = epsilon
    weight2 = (theta - thetamap[theta_idx1]) / denominator
    final_val = _linear_interpolate(val1, val2, weight2)

    return final_val


def _find_closest(sorted_list, value):
    """
    Find the indices of the two closest values to the given value in a sorted
    list.
    """

    index = bisect.bisect_left(sorted_list, value)
    if index == 0:
        return 0, 0
    if index == len(sorted_list):
        return len(sorted_list) - 1, len(sorted_list) - 1
    return index - 1, index


def _linear_interpolate(value1, value2, weight):
    """
    Linearly interpolate between two values.
    """

    return value1 * (1 - weight) + value2 * weight
