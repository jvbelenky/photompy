import numpy as np
import bisect
import warnings


def interpolate_values(lampdict, num_thetas=181, num_phis=361, overwrite=False):
    """
    Fill in the values of an .ies value dictionary with interpolation
    Requires a lampdict with a `full_vals` key
    """

    if "interp_vals" in list(lampdict.keys()):
        if not overwrite:
            msg = "Interpolated dictionary already exists. If you wish to overwrite it, set `overwrite` to True."
            warnings.warn(msg, stacklevel=2)
            return lampdict

    valdict = lampdict["full_vals"]

    newthetas = np.linspace(0, 180, num_thetas)
    newphis = np.linspace(0, 360, num_phis)

    tgrid, pgrid = np.meshgrid(newthetas, newphis)
    tflat, pflat = tgrid.flatten(), pgrid.flatten()

    intensity = get_intensity_vectorized(tflat, pflat, valdict)
    newvalues = intensity.reshape(num_phis, num_thetas)

    newdict = {}
    newdict["thetas"] = newthetas
    newdict["phis"] = newphis
    newdict["values"] = newvalues

    lampdict["interp_vals"] = newdict

    return lampdict

def get_intensity_vectorized(theta, phi, valdict):
    thetamap = valdict["thetas"]
    phimap = valdict["phis"]
    valuemap = valdict["values"]

    # Ensure theta and phi are numpy arrays
    theta = np.asarray(theta)
    phi = np.asarray(phi)

    # Range checks for theta and phi
    if np.any(theta < 0) or np.any(theta > 180):
        raise ValueError("Theta values must be between 0 and 180 degrees")
    phi = np.mod(phi, 360)  # Normalize phi values

    # Finding closest indices for phi and theta
    phi_indices = np.searchsorted(phimap, phi, side='left')
    theta_indices = np.searchsorted(thetamap, theta, side='left')

    # Handle boundary conditions for interpolation
    phi_indices = np.clip(phi_indices, 1, len(phimap)-1)
    theta_indices = np.clip(theta_indices, 1, len(thetamap)-1)

    # Compute interpolation weights
    phi_weights = (phi - phimap[phi_indices-1]) / (phimap[phi_indices] - phimap[phi_indices-1])
    theta_weights = (theta - thetamap[theta_indices-1]) / (thetamap[theta_indices] - thetamap[theta_indices-1])

    # Interpolate values
    val1 = valuemap[phi_indices-1, theta_indices-1] * (1 - phi_weights) + valuemap[phi_indices, theta_indices-1] * phi_weights
    val2 = valuemap[phi_indices-1, theta_indices] * (1 - phi_weights) + valuemap[phi_indices, theta_indices] * phi_weights
    final_val = val1 * (1 - theta_weights) + val2 * theta_weights

    return final_val
    
########## Everything below here is deprecated! #################

def get_intensity(theta, phi, valdict):
    """
    determine arbitrary intensity value anywhere on unit sphere

    theta: vertical angle value of interest
    phi: horizontal/azimuthal angle value of interest
    thetamap: existing theta value for which data is available
    phimap: existing phi vlaues for which data is available
    valuemap: array of shape (len(ph))

    """
   
    thetamap = valdict["thetas"]
    phimap = valdict["phis"]
    valuemap = valdict["values"]

    if theta < 0 or theta > 180:
        msg = "Theta must be >0 and <180 degrees, {} was passed".format(theta)
        raise ValueError(msg)

    if phi > 360 or phi < 0:
        phi = phi % 360

    if phi in phimap:
        phi_idx = np.argwhere(phimap==phi)[0][0]
    else:
        phi_idx = None
    if theta in thetamap:
        theta_idx = np.argwhere(thetamap==theta)[0][0]
    else:
        theta_idx = None

    # prevent div by zero errors
    if phi == 0:
        phi += epsilon
    if theta == 0:
        theta += epsilon

    phi_idx1, phi_idx2 = _find_closest(phimap, phi)
    theta_idx1, theta_idx2 = _find_closest(thetamap, theta)

    # Interpolate along phimap for both thetamap
    weight1 = (phi - phimap[phi_idx1]) / (phimap[phi_idx2] - phimap[phi_idx1])
    val1a = valuemap[phi_idx1][theta_idx1]
    val1b = valuemap[phi_idx2][theta_idx1]
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
