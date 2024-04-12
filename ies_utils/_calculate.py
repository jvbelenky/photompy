import numpy as np
from ._interpolate import interpolate
from ._read import read_ies_data


def total_optical_power(filename, num_thetas=181, num_phis=361, distance=1):
    """
    calculate the total optical power of a lamp given an .ies file
    
    filename: .ies file to calculate from
    num_thetas: number of vertical angles to interpolate between
    num_phis: number of horizontal angles to interpolate between
    distance: lamp distance from sensor, in meters. Generally 1. 
    """

    # load
    lampdict = read_ies_data(filename)
    valdict = lampdict["full_vals"]

    # interpolate
    interp_dict = interpolate(valdict, num_thetas, num_phis)

    # ies file is in degrees
    theta_deg = interp_dict["thetas"]
    phi_deg = interp_dict["phis"]

    # compute the area infinitesimal
    Theta_deg, Phi_deg = np.meshgrid(theta_deg, phi_deg)
    # convert to radians
    dTheta_rad = np.radians(theta_deg[1] - theta_deg[0])
    dPhi_rad = np.radians(phi_deg[1] - phi_deg[0])
    dA = distance**2 * np.sin(np.radians(Theta_deg)) * dTheta_rad * dPhi_rad

    total_power = (interp_dict["values"] * dA).sum()

    return total_power


def lamp_area(filename, units="meters", verbose=False):

    """
    return lamp area in units of m^2, ft^2 or in^2
    """

    if units.lower() not in ["meters", "feet", "inches"]:
        msg = "Argument units must be either `meters`,`feet`, or `inches"
        raise KeyError(msg)

    lampdict = read_ies_data(filename)
    if lampdict["units_type"] == 1:
        # feet
        width_ft = lampdict["width"]
        length_ft = lampdict["length"]
        width_m = lampdict["width"] / 0.3048
        length_m = lampdict["length"] / 0.3048
    elif lampdict["units_type"] == 2:
        # meters
        width_m = lampdict["width"]
        length_m = lampdict["length"]
        width_ft = lampdict["width"] * 0.3048
        length_ft = lampdict["length"] * 0.3048
    
    width_in, length_in = width_ft * 12, length_ft * 12

    if units.lower() == "feet":
        area = width_ft * length_ft
    if units.lower() == "meters":
        area = width_m * length_m
    if units.lower() == "inches":
        area = width_in * length_in
    if verbose:
        print("Area (cm2)", width_m * length_m * 100 * 100)
    return area
