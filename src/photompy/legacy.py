"""
Legacy API - Deprecated Functions

This module contains deprecated functions maintained for backward compatibility.
All functions emit DeprecationWarning when called.

For new code, use the modern IESFile API instead:
    from photompy import IESFile
    ies = IESFile.read("lamp.ies")

See docs/migration.md for migration guidance.
"""

import copy
import warnings
import numpy as np


def _deprecation_warning(old_name, new_usage):
    """Emit a deprecation warning with migration guidance."""
    warnings.warn(
        f"{old_name} is deprecated; use {new_usage} instead",
        DeprecationWarning,
        stacklevel=3,
    )


# =============================================================================
# Reading Functions
# =============================================================================


def read_ies_data(filedata, extend=True, interpolate=True):
    """
    DEPRECATED: Use IESFile.read() instead.

    Main .ies file reading function.
    Returns a lampdict dictionary for backward compatibility.
    """
    _deprecation_warning("read_ies_data", "IESFile.read()")

    from ._read import (
        load_bytes, get_version, process_keywords, process_header,
        read_angles, get_lamp_type, _format_angles, verify_valdict
    )
    from ._interpolate import interpolate_values as _interpolate_values

    raw, origin = load_bytes(filedata)
    lines = raw.decode("utf-8").split("\n")
    lines = [line.strip() for line in lines]

    lampdict = {"source": filedata}
    lampdict["version"] = get_version(lines)

    header = []
    data_start_idx = None
    tilt_value = None
    for i, line in enumerate(lines):
        if line.startswith("TILT="):
            tilt_value = line.split("=", 1)[1]
            if line == "TILT=INCLUDE":
                data_start_idx = i + 5
            else:
                data_start_idx = i + 1
            break
        else:
            header.append(line)
    keywords = process_keywords(header)
    if tilt_value is not None:
        keywords["TILT"] = tilt_value
    lampdict["keywords"] = keywords

    data = " ".join(lines[data_start_idx:]).split()
    lampdict.update(process_header(data))

    lampdict["lamp_type"] = "?"

    num_thetas = lampdict["num_vertical_angles"]
    num_phis = lampdict["num_horizontal_angles"]
    blocks = data[13:]
    thetas, phis, values = read_angles(blocks, num_thetas, num_phis)
    lampdict["original_vals"] = {
        "thetas": thetas,
        "phis": phis,
        "values": values,
    }

    photometry = lampdict["photometric_type"]
    lampdict["photometry"] = get_lamp_type(phis, photometry)

    if extend:
        _format_angles(lampdict)
    if interpolate:
        _interpolate_values(lampdict)

    return lampdict


# =============================================================================
# Writing Functions
# =============================================================================


def write_ies_data(lampdict, filename=None, valkey="original_vals"):
    """
    DEPRECATED: Use IESFile.write() instead.

    Write a lampdict object to an .ies file.
    """
    _deprecation_warning("write_ies_data", "IESFile.write()")

    from ._read import verify_valdict
    from ._write import process_row

    valdict = lampdict[valkey]
    verify_valdict(valdict)

    if valkey in ["full_vals", "interp_vals"]:
        lampdict["multiplier"] = 1

    thetas = valdict["thetas"]
    phis = valdict["phis"]
    values = valdict["values"]

    lampdict["num_vertical_angles"] = len(thetas)
    lampdict["num_horizontal_angles"] = len(phis)

    iesdata = lampdict["version"] + "\n"
    for key, val in lampdict["keywords"].items():
        if key != "TILT":
            iesdata += "[" + key + "] " + val + "\n"
        else:
            iesdata += key + "=" + val + "\n"

    row1_keys = [
        "num_lamps", "lumens_per_lamp", "multiplier",
        "num_vertical_angles", "num_horizontal_angles",
        "photometric_type", "units_type", "width", "length", "height"
    ]
    row2_keys = ["ballast_factor", "future_use", "input_watts"]
    row1 = [lampdict[key] for key in row1_keys]
    row2 = [lampdict[key] for key in row2_keys]
    iesdata += " ".join([str(val) for val in row1]) + "\n"
    iesdata += " ".join([str(val) for val in row2]) + "\n"
    iesdata += process_row(thetas)
    iesdata += process_row(phis)
    candelas = ""
    for row in values:
        candelas += process_row(row, sigfigs=2)
    iesdata += candelas

    if filename is not None:
        with open(filename, "w", encoding="utf-8") as newfile:
            newfile.write(iesdata)
    else:
        return iesdata.encode("utf-8")


def scale_lamp_to_total(total_power, ref_lamp, outfile):
    """
    DEPRECATED: Use IESFile.scale_to_total() instead.

    Create a new IES file with a set total optical power value.
    """
    _deprecation_warning(
        "scale_lamp_to_total",
        "ies = IESFile.read(file); ies.scale_to_total(power); ies.write(outfile)"
    )

    from .ies import IESFile
    ies_file = copy.deepcopy(IESFile.read(ref_lamp))
    ies_file.scale_to_total(total_power)
    ies_file.write(outfile, which="full")


def scale_lamp_to_max(max_val, ref_lamp, outfile):
    """
    DEPRECATED: Use IESFile.scale_to_max() instead.

    Create a new IES file with a set maximum irradiance value.
    """
    _deprecation_warning(
        "scale_lamp_to_max",
        "ies = IESFile.read(file); ies.scale_to_max(max_val); ies.write(outfile)"
    )

    from .ies import IESFile
    ies_file = copy.deepcopy(IESFile.read(ref_lamp))
    ies_file.scale_to_max(max_val)
    ies_file.write(outfile, which="full")


# =============================================================================
# Calculation Functions
# =============================================================================


def total_optical_power(data, num_thetas=181, num_phis=361, distance=1):
    """
    DEPRECATED: Use IESFile.photometry.total_optical_power() instead.

    Calculate the total optical power of a lamp.
    """
    _deprecation_warning(
        "total_optical_power",
        "IESFile.read(file).photometry.total_optical_power()"
    )

    import os
    import pathlib
    from ._read import verify_valdict
    from ._calculate import _compute_total_power

    if isinstance(data, (str, pathlib.PosixPath)) and os.path.isfile(data):
        from .ies import IESFile
        ies_file = IESFile.read(data)
        interp_phot = ies_file.photometry.interpolated(num_thetas, num_phis)
        valdict = {
            "thetas": interp_phot.thetas,
            "phis": interp_phot.phis,
            "values": interp_phot.values,
        }
        return _compute_total_power(valdict)
    elif isinstance(data, dict):
        verify_valdict(data)
        return _compute_total_power(data)
    else:
        raise ValueError("data must be either an .ies file or a dict object")


def lamp_area(filename, units="meters", verbose=False):
    """
    DEPRECATED: Use IESFile.lamp_area() instead.

    Return lamp area in units of m^2, ft^2 or in^2.
    """
    _deprecation_warning(
        "lamp_area",
        "IESFile.read(file).lamp_area(units)"
    )

    if units.lower() not in ["meters", "feet", "inches"]:
        raise KeyError("Argument units must be either `meters`, `feet`, or `inches`")

    from .ies import IESFile

    ies_file = IESFile.read(filename)
    area = ies_file.lamp_area(units)

    if verbose:
        area_m2 = ies_file.lamp_area("meters")
        print("Area (cm2)", area_m2 * 100 * 100)

    return area


# =============================================================================
# Interpolation Functions
# =============================================================================


def interpolate_values(lampdict, num_thetas=181, num_phis=361, overwrite=False):
    """
    DEPRECATED: Use IESFile.photometry.interpolated() instead.

    Fill in the values of an .ies value dictionary with interpolation.
    Mutates lampdict in place for backward compatibility.
    """
    _deprecation_warning(
        "interpolate_values",
        "IESFile.read(file).photometry.interpolated(num_thetas, num_phis)"
    )

    from ._interpolate import interpolate_values as _interpolate_values
    return _interpolate_values(lampdict, num_thetas, num_phis, overwrite)


def get_intensity(theta, phi, valdict):
    """
    DEPRECATED: Use IESFile.photometry.get_intensity() instead.

    Determine arbitrary intensity value anywhere on unit sphere.
    """
    _deprecation_warning(
        "get_intensity",
        "IESFile.read(file).photometry.get_intensity(theta, phi)"
    )

    from ._interpolate import get_intensity as _get_intensity
    return _get_intensity(theta, phi, valdict)


# =============================================================================
# Plotting Functions
# =============================================================================


def plot_ies(
    fdata,
    plot_type="polar",
    which="interpolated",
    elev=-90,
    azim=90,
    title=None,
    figsize=(6, 4),
    show_cbar=False,
    alpha=0.7,
    cmap="rainbow",
):
    """
    DEPRECATED: Use IESFile.plot() instead.

    Central plotting function for IES files.
    """
    _deprecation_warning("plot_ies", "IESFile.read(file).plot()")

    from ._plot import plot_ies as _plot_ies
    return _plot_ies(
        fdata=fdata,
        plot_type=plot_type,
        which=which,
        elev=elev,
        azim=azim,
        title=title,
        figsize=figsize,
        show_cbar=show_cbar,
        alpha=alpha,
        cmap=cmap,
    )
