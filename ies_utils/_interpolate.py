import bisect
import numpy as np


def get_intensity(theta, phi, thetamap, phimap, valuemap):
    """
    determine arbitrary intensity value anywhere on unit sphere

    theta: vertical angle value of interest
    phi: horizontal/azimuthal angle value of interest
    thetamap: existing theta value for which data is available
    phimap: existing phi vlaues for which data is available
    valuemap: array of shape (len(ph))

    """
    epsilon = np.finfo(np.float64).eps

    if theta < 0 or theta > 180:
        raise Exception(
            "Theta must be >0 and <180 degrees, value provided was{:s}".format(theta)
        )

    if phi > 360 or phi < 0:
        phi = phi % 360

    # prevent div by zero errors
    if phi == 0:
        phi += epsilon
    if theta == 0:
        theta += epsilon

    valuemap = valuemap.reshape(phimap.shape[0], thetamap.shape[0])

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
