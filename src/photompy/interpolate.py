import numpy as np
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

    intensity = get_intensity(tflat, pflat, valdict)
    newvalues = intensity.reshape(num_phis, num_thetas)

    newdict = {}
    newdict["thetas"] = newthetas
    newdict["phis"] = newphis
    newdict["values"] = newvalues

    lampdict["interp_vals"] = newdict

    return lampdict


def get_intensity(theta, phi, valdict):
    """
    determine arbitrary intensity value anywhere on unit sphere

    theta: arraylike of vertical angle value of interest
    phi: arraylike of horizontal/azimuthal angle value of interest
    valdict: value dictionary containing theta, phi, value triplets
    """
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
