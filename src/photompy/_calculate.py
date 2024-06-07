import numpy as np
import pathlib
import os
from ._interpolate import interpolate_values
from ._read import read_ies_data, verify_valdict


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
        valdict = _load_interpdict(data,num_thetas,num_phis)
        result = _compute_total_power(valdict)
    elif isinstance(data, dict):
        verify_valdict(data) # will raise errors if valdict is malformed
        result = _compute_total_power(data)
    else:
        raise ValueError("data must be either an .ies file or a dict object")
    return result
    
def _load_interpdict(filename, num_thetas, num_phis):
    """
    load a dictionary with interpolated values, and 
    interpolate if it does not exist
    """
    lampdict = read_ies_data(filename)
    try:
        interp_dict = lampdict["interp_vals"]
    except KeyError:
        interpolate_values(lampdict, num_thetas=num_thetas, num_phis=num_phis)
        interp_dict = lampdict["interp_vals"]

    return lampdict['interp_vals']
        

def _compute_total_power(valdict):
    """compute the total optical power"""
    values = valdict['values']
    phis = valdict['phis']
    thetas = valdict['thetas']

    thetastep = thetas[1]-thetas[0]
    thetasums = values.sum(axis=0) / len(phis)
    thetas1 = np.maximum(0, thetas - thetastep / 2)  # Avoid negative angles
    thetas2 = thetas + thetastep / 2
    areas = _compute_frustrum_area(thetas1, thetas2)
    total_power = (thetasums*areas).sum()
    return total_power
    

def _compute_frustrum_area(theta1, theta2):
    a1 = 2*np.pi*(1 - np.cos(np.radians(theta1))) # r^2 = 1
    a2 = 2*np.pi*(1 - np.cos(np.radians(theta2))) # r^2 = 1
    return a2 - a1

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
        width_m = lampdict["width"] * 0.3048
        length_m = lampdict["length"] * 0.3048
    elif lampdict["units_type"] == 2:
        # meters
        width_m = lampdict["width"]
        length_m = lampdict["length"]
        width_ft = lampdict["width"] / 0.3048
        length_ft = lampdict["length"] / 0.3048

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
