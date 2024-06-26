import sys
from pathlib import Path
from photompy
 import *

if len(sys.argv) > 1:
    filename = Path(sys.argv[1])
else:
    filename = Path("./tests/ies_files/B1 module.ies")

# read
lampdict = read_ies_data(filename)

# calculate
power = total_optical_power(filename)
m = lamp_area(filename, units="meters")

# interpolate
interpolate_values(lampdict, overwrite=True, num_thetas=361, num_phis=721)
interpdict = lampdict['interp_vals']

# write to new file
newfile = Path("tests/ies_files/write_test_original.ies")
write_ies_data(filename=newfile, lampdict=lampdict, valkey="original_vals")
read_ies_data(newfile)
newfile = Path("tests/ies_files/write_test_full.ies")
write_ies_data(filename=newfile, lampdict=lampdict, valkey="interp_vals")
read_ies_data(newfile)

# # plot
# plot_ies(filename, "original")
# plot_ies(filename, "full")
# plot_ies(filename, "interpolated")
plot_ies(filename)

# plot_valdict_polar(interpdict)
# plot_valdict_cartesian(interpdict)
