import numpy as np
from ._interpolate import get_intensity
from ._read import read_ies_data


def total_optical_power(filename, num=100):
    """
    calculate the total optical power of a lamp given an .ies file
    """
    lampdict = read_ies_data(filename)
    thetamap = lampdict["full_vals"]["thetas"]
    phimap = lampdict["full_vals"]["phis"]
    valuemap = lampdict["full_vals"]["values"].reshape(len(phimap), len(thetamap))

    # ies file is in degrees
    theta_deg = np.linspace(0, 180, num=num)
    phi_deg = np.linspace(0, 360, num=num)

    # Create a meshgrid for theta and phi in degrees
    Theta_deg, Phi_deg = np.meshgrid(theta_deg, phi_deg)

    # convert to radians because that's how the infinitesimal element works
    dTheta_rad = np.radians(theta_deg[1] - theta_deg[0])
    dPhi_rad = np.radians(phi_deg[1] - phi_deg[0])
    dA = np.sin(np.radians(Theta_deg)) * dTheta_rad * dPhi_rad

    # flatten mesh
    thetaflat, phiflat = Theta_deg.reshape(-1), Phi_deg.reshape(-1)
    # retrieve intensity map
    intensity = [
        get_intensity(theta, phi, thetamap, phimap, valuemap)
        for theta, phi in zip(thetaflat, phiflat)
    ]
    # multiply by area differential
    total_power = (np.array(intensity).reshape(num, num) * dA).sum()

    return total_power
