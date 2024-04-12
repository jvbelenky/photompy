import sys
from pathlib import Path
from ies_utils import (
    read_ies_data,
    write_ies_data,
    plot_ies,
    total_optical_power,
    lamp_area,
    interpolate
)

if len(sys.argv) > 1:
    filename = Path(sys.argv[1])
else:
    filename = Path("./tests/ies_files/LLIA001477-003.ies")

# read
lampdict = read_ies_data(filename)

# calculate
power = total_optical_power(filename)
m = lamp_area(filename, units="meters")

# interpolate
valdict = lampdict['full_vals']
interpdict = interpolate(valdict,num_thetas=181,num_phis=361)

# write to new file
newfile = Path("tests/ies_files/write_test_original.ies")
write_ies_data(filename=newfile, lampdict=lampdict, valkey="original_vals")
read_ies_data(newfile)
newfile = Path("tests/ies_files/write_test_full.ies")
write_ies_data(filename=newfile, lampdict=lampdict, valkey="full_vals")
read_ies_data(newfile)

# plot
plot_ies(filename, "original")
plot_ies(filename, "full")
plot_ies(filename, "interpolated")
