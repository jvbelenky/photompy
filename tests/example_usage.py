import sys
import numpy as np
from ies_utils import read_ies_data, get_intensity, get_coords, plot_ies, total_optical_power

if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    filename = "tests/LLIA001477-003.ies"

lampdict = read_ies_data(filename)

thetamap = lampdict["extended_vals"]["thetas"]
phimap = lampdict["extended_vals"]["phis"]
valuemap = lampdict["extended_vals"]["values"].reshape(len(phimap), len(thetamap))

# make up some test values
newthetas = np.linspace(0, 180, 100)
newphis = np.linspace(0, 360, 100)

thetaflat, phiflat = get_coords(newthetas, newphis, which="polar")

intensity = [
    get_intensity(theta, phi, thetamap, phimap, valuemap)
    for theta, phi in zip(thetaflat, phiflat)
]

x, y, z = get_coords(newthetas, newphis, which="cartesian")

power = total_optical_power(filename)

# plot_ies(filename)
print("Execution successful")
