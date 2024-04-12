import sys
import numpy as np
from ies_utils import read_ies_data, write_ies_data, get_intensity, get_coords, plot_ies, total_optical_power, lamp_area

if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    filename = "tests/LLIA001477-003.ies"

lampdict = read_ies_data(filename)

thetamap = lampdict["full_vals"]["thetas"]
phimap = lampdict["full_vals"]["phis"]
valuemap = lampdict["full_vals"]["values"].reshape(len(phimap), len(thetamap))

# make up some test values
newthetas = np.linspace(0, 180, 100)
newphis = np.linspace(0, 360, 100)

thetaflat, phiflat = get_coords(newthetas, newphis, which="polar")

intensity = [
    get_intensity(theta, phi, thetamap, phimap, valuemap)
    for theta, phi in zip(thetaflat, phiflat)
]

x, y, z = get_coords(newthetas, newphis, which="cartesian")

# calculate
power = total_optical_power(filename)
m = lamp_area(filename,units='meters')
ft = lamp_area(filename,units='feet')
inch = lamp_area(filename,units='inches')

# write to new file
newfile = 'tests/write_test_original.ies'
write_ies_data(filename=newfile, lampdict=lampdict, valkey='original_vals')
read_ies_data(newfile)
newfile = 'tests/write_test_full.ies'
write_ies_data(filename=newfile, lampdict=lampdict, valkey='original_vals')
read_ies_data(newfile)


# plot_ies(filename)
print("Execution successful")
