"""
Internal read helpers.

This module contains helper functions for parsing IES files.
These are internal implementation details, not part of the public API.
"""

import os
from pathlib import Path
import warnings
import numpy as np
from collections import Counter


def _get_max_path() -> int:
    """Get the maximum path length for the current platform."""
    # POSIX: ask the kernel
    if hasattr(os, "pathconf"):
        try:  # might fail on a weird FS
            return os.pathconf("/", "PC_PATH_MAX")
        except (OSError, ValueError):
            pass  # fall through to default

    # Windows: use Win32 header value
    if os.name == "nt":
        try:
            import ctypes.wintypes
            return ctypes.wintypes.MAX_PATH
        except Exception:
            return 260

    # Last-ditch, reasonable POSIX default
    return 4096  # Linux usually reports 4096


_MAX_PATH = _get_max_path()


def load_bytes(src, *, encoding: str = "utf-8"):
    """
    Normalise every input flavour to `bytes`.

    Returns:
        data: bytes - raw content
        origin: Path | None - where it came from (if a real file)
    """
    # bytes already
    if isinstance(src, (bytes, bytearray)):
        return bytes(src), None

    # open file object
    if hasattr(src, "read"):
        raw = src.read()
        if isinstance(raw, str):
            raw = raw.encode(encoding, "surrogateescape")
        return raw, None

    # string of some sort
    if isinstance(src, str):
        # in-memory text, or path
        if "TILT=" in src.upper():
            return src.encode(encoding, "surrogateescape"), None
        else:
            return _read_file(src)

    # Path
    if isinstance(src, Path):
        return _read_file(src)

    raise TypeError(f"Cannot interpret {type(src).__name__} as IES data")


def _read_file(src):
    """Read bytes from a file path."""
    p = Path(src)
    if not p.is_file():
        raise FileNotFoundError("Invalid path")
    return p.read_bytes(), p


def get_version(lines, strict=False):
    """Extract IES version from file lines."""
    if lines[0].startswith("IESNA"):
        version = lines[0]
    else:
        version = "Not specified"
        warnings.warn('File does not begin with "IESNA" and may be malformed')
    return version


def process_keywords(header):
    """Process header lines into a keyword dictionary."""
    # do some cleanup
    keylines = [line for line in header if line.startswith("[")]
    keys = [line.split("]")[0].strip("[") for line in keylines]
    vals = ["".join(line.split("]")[1:]) for line in keylines]
    vals = [val.strip() for val in vals]

    # make all keys unique
    non_unique_keys = [k for (k, v) in Counter(keys).items() if v > 1 and k != "MORE"]
    for degen_key in non_unique_keys:
        j = 1
        for i, key in enumerate(keys):
            if key == degen_key:
                keys[i] = degen_key + "-" + str(j)
                j += 1

    # combine all the MORE lines into single strings
    newkeys, newvals = [], []
    for i in range(len(keylines)):
        j = 0
        try:
            if keys[i] == "MORE":
                continue
            while keys[i + j + 1] == "MORE":
                j += 1
            newkeys.append(keys[i])
            k = i + j + 1
            newvals.append(" ".join(vals[i:k]))
        except IndexError:
            newkeys.append(keys[i])
            k = i + j + 1
            newvals.append(" ".join(vals[i:k]))
            continue

    keyword_dict = dict(zip(newkeys, newvals))
    return keyword_dict


def process_header(data):
    """Process the numeric, non-keyword header data."""
    return {
        "num_lamps": int(data[0]),
        "lumens_per_lamp": float(data[1]),
        "multiplier": float(data[2]),
        "num_vertical_angles": int(data[3]),
        "num_horizontal_angles": int(data[4]),
        "photometric_type": int(data[5]),
        "units_type": int(data[6]),
        "width": float(data[7]),
        "length": float(data[8]),
        "height": float(data[9]),
        "ballast_factor": float(data[10]),
        "future_use": float(data[11]),
        "input_watts": float(data[12]),
    }


def _detect_decimal_places(tokens):
    """Detect max decimal places from numeric string tokens."""
    max_dp = 0
    for t in tokens:
        if '.' in t:
            dp = len(t.split('.')[1])
            max_dp = max(max_dp, dp)
    return max_dp


def read_angles(data, num_thetas, num_phis):
    """Read angle and value data from numeric tokens."""
    # read vertical angles
    v_start = 0
    v_end = num_thetas
    theta_tokens = data[v_start:v_end]
    thetas = np.array(list(map(float, theta_tokens)))

    # read horizontal angles
    h_start = v_end
    h_end = h_start + num_phis
    phi_tokens = data[h_start:h_end]
    phis = np.array(list(map(float, phi_tokens)))

    # read values (1d and 2d)
    val_start = h_end
    num_values = num_thetas * num_phis
    val_end = val_start + num_values
    val_tokens = data[val_start:val_end]
    values = np.array(list(map(float, val_tokens)))
    values = values.reshape(num_phis, num_thetas)

    # detect precision from raw text before float conversion
    precision = (
        _detect_decimal_places(theta_tokens),
        _detect_decimal_places(phi_tokens),
        _detect_decimal_places(val_tokens),
    )

    return thetas, phis, values, precision


def get_lamp_type(phis, photometry):
    """
    Determine lamp photometry type (A, B, and C), and lateral lamp symmetry.

    Lamp types: ["A90", "A-90", "B90", "B-90", "C0", "C90", "C180", "C360"]
    """
    lamp_type = "?"

    if photometry == 1:
        if phis[0] != 0:
            msg = "Listed photometric type does not match first horizontal \
                angle value. Values will not be mirrored."
            warnings.warn(msg, stacklevel=2)
        lamp_type = "C"
        if phis[-1] not in [0, 90, 180, 360]:
            msg = "Listed photometric type does not match last horizontal \
                angle value. Values will not be mirrored."
            warnings.warn(msg, stacklevel=2)
        for val in [0, 90, 180, 360]:
            if phis[-1] == val:
                lamp_type += str(val)
    elif photometry in [2, 3]:
        if photometry == 2:
            lamp_type = "B"
        elif photometry == 3:
            lamp_type = "A"
        if phis[-1] != 90:
            msg = "Listed photometric type does not match last horizontal \
                angle value. Values will not be mirrored."
            warnings.warn(msg, stacklevel=2)
        if phis[0] not in [-90, 0]:
            msg = "Listed photometric type does not match first horizontal \
                angle value. Values will not be mirrored."
            warnings.warn(msg, stacklevel=2)
        for val in [-90, 0]:
            if phis[0] == val:
                lamp_type += str(val)
    else:
        msg = "Photometry type could not be determined. \
            Values will not be mirrored."
        warnings.warn(msg, stacklevel=2)

    # list only currently supported lamp types
    if lamp_type not in ["C0", "C90", "C180", "C360"]:
        msg = "Photometry type {} not currently supported. \
            Values will not be mirrored.".format(lamp_type)
        warnings.warn(msg, stacklevel=2)

    return lamp_type


def _format_angles(lampdict):
    """
    Read the lamp symmetry and mirror the values accordingly.

    TODO: add support for type A and B photometry
    https://support.agi32.com/support/solutions/articles/22000209748
    """
    newdict = {}
    lampdict["full_vals"] = {}

    valdict = lampdict["original_vals"]
    lamp_type = lampdict["lamp_type"]

    newthetas = valdict["thetas"].copy()

    if lamp_type == "C0":
        # total radial symmetry
        phis = valdict["phis"].copy()
        newphis = np.arange(0, 360)
        values = valdict["values"].copy().reshape(-1)
        newvals = np.tile(values, 360).reshape(-1, 360)

    elif lamp_type == "C90":
        # quaternary symmetry; each quadrant is identical
        phis = valdict["phis"].copy()
        phis2 = phis[1:] + 90
        phis3 = phis[1:] + 180
        phis4 = phis[1:] + 270
        newphis = np.concatenate((phis, phis2, phis3, phis4))

        values = valdict["values"].copy()
        vals1 = values[:-1]
        vals2 = np.flip(values, axis=0)
        vals3 = np.concatenate((vals1, vals2))
        vals4 = np.flip(vals3[:-1], axis=0)
        newvals = np.concatenate((vals3, vals4))

    elif lamp_type == "C180":
        # bilateral symmetry
        phis = valdict["phis"].copy()
        phis2 = phis[1:] + 180
        newphis = np.concatenate((phis, phis2))

        values = valdict["values"].copy()
        vals1 = values[:-1]
        vals2 = np.flip(values, axis=0)
        newvals = np.concatenate((vals1, vals2))

    else:
        # either lamp_type is C360 (original vals already fully extended)
        # or lamp type is not supported
        newphis = valdict["phis"].copy()
        newthetas = valdict["thetas"].copy()
        newvals = valdict["values"].copy()

    # fill in values of theta 90-180 if not provided
    if newthetas[-1] == 90:
        step = newthetas[-1] - newthetas[-2]
        extrathetas = []
        val = newthetas[-1]
        while val < 180:
            val = val + step
            extrathetas.append(val)
        if extrathetas[-1] != 180:
            warnings.warn(
                "Step function for filling out extra vertical angles did not \
                produce a final value of 180"
            )
        newthetas = np.concatenate((newthetas, extrathetas))
        extravals = np.zeros((len(newphis), len(extrathetas)))
        newvals = np.concatenate((newvals.T, extravals.T)).T

    # use candela multiplier
    mult = lampdict["multiplier"]

    newdict["thetas"] = newthetas
    newdict["phis"] = newphis
    newdict["values"] = newvals * mult

    verify_valdict(newdict)

    lampdict["full_vals"] = newdict

    return lampdict


def verify_valdict(valdict):
    """Verify that a valdict has the required structure."""
    keys = list(valdict.keys())
    if not all(x in keys for x in ["thetas", "phis", "values"]):
        raise KeyError

    thetas = valdict["thetas"]
    phis = valdict["phis"]
    values = valdict["values"]

    # verify data shape
    if not values.shape == (len(phis), len(thetas)):
        msg = "Shape of candela values {} does not match number of vertical and \
            horizontal angles {}".format(values.shape, (len(phis), len(thetas)))
        raise ValueError(msg)
