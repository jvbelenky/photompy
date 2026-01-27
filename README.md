PhotomPy: Photometric Python
===========================
A library for reading, writing, and viewing photometric files.

<!-- Installation -->
## Installation

Install with pip:

	pip install photompy

Alternatively, clone the repo and build locally:

	git clone https://github.com/jvbelenky/photompy.git
    cd photompy
    python setup.py sdist
    pip install .


<!-- USAGE EXAMPLES -->
## Usage

### Modern API (Recommended)

The recommended way to work with IES files is through the `IESFile` class:

```python
from photompy import IESFile

# Read an IES file
ies = IESFile.read("lamp.ies")

# Access photometry data
print(ies.photometry.thetas)  # vertical angles
print(ies.photometry.phis)    # horizontal angles
print(ies.photometry.values)  # candela values

# Calculate total optical power
power = ies.photometry.total_optical_power()

# Get intensity at specific angles
intensity = ies.photometry.get_intensity(theta=45, phi=0)

# Plot the photometry
fig, ax = ies.plot(plot_type="polar")
fig, ax = ies.plot(plot_type="cartesian", elev=45, azim=30)

# Scale values
ies.scale_to_max(5000)           # Scale to max candela value
ies.scale_to_total(1000)         # Scale to total power
ies.scale_to_center(2500)        # Scale to center intensity
ies.scale(2.0)                   # Scale by factor

# Write to file
ies.write("output.ies")                    # Write original angles
ies.write("output.ies", which="full")      # Write expanded angles
ies.write("output.ies", which="interp")    # Write interpolated angles

# Access header information
print(ies.header.units)           # FEET or METERS
print(ies.header.width)           # luminous width
print(ies.header.length)          # luminous length
print(ies.header.input_watts)     # input watts
```

### Legacy API (Deprecated)

The following functions are still available but deprecated. They will emit deprecation warnings:

```python
from photompy import read_ies_data, write_ies_data, total_optical_power, plot_ies

# These still work but will warn
lampdict = read_ies_data(filename)
power = total_optical_power(filename)
fig, ax = plot_ies(filename)
```

See `docs/migration.md` for a complete guide on migrating from the legacy API.

### Working with Photometry Directly

For advanced use cases, you can work with the `Photometry` class directly:

```python
from photompy import IESFile

ies = IESFile.read("lamp.ies")
phot = ies.photometry

# Get expanded (mirrored) photometry
expanded = phot.expanded()

# Get interpolated photometry
interpolated = phot.interpolated(num_thetas=361, num_phis=721)
```

### Simple calculations

```python
from photompy import total_optical_power, lamp_area

power = total_optical_power(filename)
luminous_area = lamp_area(filename, units="meters")
```

### Writing files

To scale and write IES files:

```python
from photompy import scale_lamp_to_max, scale_lamp_to_total

# Scale to specific maximum value
scale_lamp_to_max(5000, "input.ies", "output.ies")

# Scale to specific total optical power
scale_lamp_to_total(1000, "input.ies", "output.ies")
```

### Generating files from angular distribution tables

Create IES or LDT files directly from numpy arrays:

```python
from photompy import create_ies, create_ldt
import numpy as np

# Define angular distribution
thetas = np.linspace(0, 90, 19)  # vertical angles
phis = np.array([0])              # single plane (axially symmetric)
values = np.cos(np.deg2rad(thetas))[None, :] * 1000  # Lambertian distribution

# Create IES file (required parameters per LM-63 spec)
ies = create_ies(
    thetas, phis, values,
    manufacturer="Acme Lighting",
    lumcat="DL-100",
    test="Performance Test 2026-001",
    testlab="Acme Test Lab",
    issuedate="2026-01-27",
    input_watts=15,
)
ies.write("downlight.ies")

# Create LDT file (EULUMDAT format)
ldt = create_ldt(
    thetas, phis, values,
    manufacturer="Acme Lighting",
    luminaire_name="Downlight DL-100",
    luminous_width=50,   # mm
    luminous_length=50,  # mm
)
ldt.write("downlight.ldt")
```

<!-- ROADMAP -->
## Roadmap

- [x] PhotometricData and AngleData objects (IESFile and Photometry classes)
- [\] Generate .ies/.ldt files from an angular distribution table
- [x] Type A and B photometry support
- [x] Dialux file (.ldt) support
- [\] More extensive write support


<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<!-- CONTACT -->
## Contact

Vivian Belenky - jvb@osluv.org
