# Migration Guide: Legacy API to Modern API

This guide helps you migrate from the deprecated legacy API to the modern `IESFile`-based API.

## Quick Reference

| Legacy Function | Modern Equivalent |
|----------------|-------------------|
| `read_ies_data(filename)` | `IESFile.read(filename)` |
| `lampdict["original_vals"]` | `ies_file.photometry` |
| `lampdict["full_vals"]` | `ies_file.photometry.expanded()` |
| `lampdict["interp_vals"]` | `ies_file.photometry.interpolated()` |
| `total_optical_power(filename)` | `ies_file.photometry.total_optical_power()` |
| `plot_ies(filename)` | `ies_file.plot()` |
| `scale_lamp_to_max(val, file, out)` | `ies_file.scale_to_max(val); ies_file.write(out)` |
| `scale_lamp_to_total(val, file, out)` | `ies_file.scale_to_total(val); ies_file.write(out)` |
| `write_ies_data(lampdict, filename)` | `ies_file.write(filename)` |
| `lamp_area(filename)` | `ies_file.header.width * ies_file.header.length` |
| `lampdict["units_type"]` | `ies_file.header.units` |
| `lampdict["width"]` | `ies_file.header.width` |
| `lampdict["length"]` | `ies_file.header.length` |
| `lampdict["multiplier"]` | Always `1` in modern API (applied on read) |

## Detailed Migration Examples

### Reading IES Files

**Legacy:**
```python
from photompy import read_ies_data

lampdict = read_ies_data("lamp.ies")
thetas = lampdict["original_vals"]["thetas"]
phis = lampdict["original_vals"]["phis"]
values = lampdict["original_vals"]["values"]
```

**Modern:**
```python
from photompy import IESFile

ies = IESFile.read("lamp.ies")
thetas = ies.photometry.thetas
phis = ies.photometry.phis
values = ies.photometry.values
```

### Accessing Extended/Mirrored Values

**Legacy:**
```python
lampdict = read_ies_data("lamp.ies")
full_thetas = lampdict["full_vals"]["thetas"]
full_phis = lampdict["full_vals"]["phis"]
full_values = lampdict["full_vals"]["values"]
```

**Modern:**
```python
ies = IESFile.read("lamp.ies")
expanded = ies.photometry.expanded()
full_thetas = expanded.thetas
full_phis = expanded.phis
full_values = expanded.values
```

### Accessing Interpolated Values

**Legacy:**
```python
from photompy import read_ies_data, interpolate_values

lampdict = read_ies_data("lamp.ies")
# Optionally customize interpolation
interpolate_values(lampdict, num_thetas=361, num_phis=721)
interp_vals = lampdict["interp_vals"]
```

**Modern:**
```python
ies = IESFile.read("lamp.ies")
interpolated = ies.photometry.interpolated(num_thetas=361, num_phis=721)
# Access as Photometry object
thetas = interpolated.thetas
phis = interpolated.phis
values = interpolated.values
```

### Calculating Total Optical Power

**Legacy:**
```python
from photompy import total_optical_power

power = total_optical_power("lamp.ies")
# Or from dict
power = total_optical_power(valdict)
```

**Modern:**
```python
ies = IESFile.read("lamp.ies")
power = ies.photometry.total_optical_power()
# Or use the convenience alias
power = ies.photometry.total()
```

### Plotting

**Legacy:**
```python
from photompy import plot_ies

fig, ax = plot_ies("lamp.ies", plot_type="polar")
fig, ax = plot_ies("lamp.ies", plot_type="cartesian", which="full")
```

**Modern:**
```python
ies = IESFile.read("lamp.ies")
fig, ax = ies.plot(plot_type="polar")
fig, ax = ies.plot(plot_type="cartesian", which="full")
```

### Scaling and Writing

**Legacy:**
```python
from photompy import scale_lamp_to_max, scale_lamp_to_total

scale_lamp_to_max(5000, "input.ies", "output.ies")
scale_lamp_to_total(1000, "input.ies", "output.ies")
```

**Modern:**
```python
import copy
from photompy import IESFile

# Scale to max
ies = copy.deepcopy(IESFile.read("input.ies"))
ies.scale_to_max(5000)
ies.write("output.ies", which="full")

# Scale to total
ies = copy.deepcopy(IESFile.read("input.ies"))
ies.scale_to_total(1000)
ies.write("output.ies", which="full")
```

### Accessing Header Information

**Legacy:**
```python
lampdict = read_ies_data("lamp.ies")
units = lampdict["units_type"]  # 1=feet, 2=meters
width = lampdict["width"]
length = lampdict["length"]
input_watts = lampdict["input_watts"]
```

**Modern:**
```python
ies = IESFile.read("lamp.ies")
units = ies.header.units  # Units.FEET or Units.METERS
width = ies.header.width
length = ies.header.length
input_watts = ies.header.input_watts
```

## Key Differences

### Multiplier Handling
- **Legacy:** The `multiplier` value was stored separately and could be accessed/modified
- **Modern:** The multiplier is applied automatically when reading. `IESFile` always has multiplier=1 internally.

### Data Structure
- **Legacy:** Used nested dictionaries (`lampdict["original_vals"]["values"]`)
- **Modern:** Uses dataclasses with attributes (`ies.photometry.values`)

### Immutability
- **Modern API** uses frozen dataclasses for headers, making them immutable. Use `ies.update()` or `ies.header.update()` to create modified copies.

### Caching
- **Modern API** caches expanded and interpolated photometry for efficiency. Subsequent calls return the cached result.

## Suppressing Deprecation Warnings

If you must use legacy functions temporarily, you can suppress warnings:

```python
import warnings
from photompy import read_ies_data

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    lampdict = read_ies_data("lamp.ies")
```

However, we recommend migrating to the modern API as legacy functions may be removed in future versions.
