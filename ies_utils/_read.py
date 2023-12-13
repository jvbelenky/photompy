from pathlib import Path
import warnings
import numpy as np


def _read_file(path_to_file):
    filepath = Path(path_to_file)
    filetype = filepath.suffix.lower()
    if filetype != ".ies":
        raise Exception("File must be .ies, not {:s}".format(filetype))
    string = filepath.read_text()
    lines = string.split("\n")

    return lines


def _get_version(lines):
    if lines[0].startswith("IES"):
        version = lines[0]
    else:
        version = "Not specified"
        warnings.warn('File does not begin with "IES" and may be malformed')
    return version


def _process_keywords(header, lampdict):
    """
    Placeholder. Eventually to be reformatted to properly capture keyword data.
    """
    lampdict["Header"] = header
    return lampdict


def _process_header(data, lampdict):
    """
    Process the numeric, non-keyword header data
    """

    lampdict["num_lamps"] = int(data[0])
    lampdict["lumens_per_lamp"] = float(data[1])
    lampdict["multiplier"] = float(data[2])
    lampdict["num_vertical_angles"] = int(data[3])
    lampdict["num_horizontal_angles"] = int(data[4])
    lampdict["photometric_type"] = int(data[5])
    lampdict["units_type"] = int(data[6])
    lampdict["width"] = float(data[7])
    lampdict["length"] = float(data[8])
    lampdict["height"] = float(data[9])
    lampdict["ballast_factor"] = float(data[10])
    lampdict["future_use"] = float(data[11])
    lampdict["input_watts"] = float(data[12])

    return lampdict


def _read_angles(data, lampdict):
    num_thetas = lampdict["num_vertical_angles"]
    num_phis = lampdict["num_horizontal_angles"]

    valdict = {}

    # read vertical angles
    v_start = 13
    v_end = v_start + num_thetas
    valdict["thetas"] = np.array(list(map(float, data[v_start:v_end])))

    # read horizontal angles
    h_start = v_end
    h_end = h_start + num_phis
    valdict["phis"] = np.array(list(map(float, data[h_start:h_end])))

    # read values (1d and 2d)
    val_start = h_end
    num_values = num_thetas * num_phis
    val_end = val_start + num_values
    vals = data[val_start:val_end]
    values = np.array(list(map(float, vals)))
    valdict["values"] = values.reshape(num_phis, num_thetas)

    lampdict["original_vals"] = valdict

    return lampdict


def _get_lamp_type(lampdict):
    """
    Determine lamp photometry type (A, B, and C), and lateral lamp symmetry
    (0, 90, 180, 360); determine if values imply that it is possible to extend
    the angles along the entire unit sphere.
    Lamp types: ["A90", "A-90", "B90", "B-90", "C0", "C90", "C180", "C360"]
    Currently, only "C" photometries are supported.
    """

    extend_values = False
    lamp_type = "?"

    phis = lampdict["original_vals"]["phis"]
    photometry = lampdict["photometric_type"]

    if photometry == 1:
        if phis[0] != 0:
            warnings.warn(
                "Listed photometric type does not match first horizontal \
                angle value. Values will not be mirrored."
            )
        lamp_type = "C"
        if phis[-1] not in [0, 90, 180, 360]:
            warnings.warn(
                "Listed photometric type does not match last horizontal \
                angle value. Values will not be mirrored."
            )
        for val in [0, 90, 180, 360]:
            if phis[-1] == val:
                lamp_type += str(val)
                extend_values = True
    elif photometry in [2, 3]:
        if photometry == 2:
            lamp_type = "B"
        elif photometry == 3:
            lamp_type = "A"
        if phis[-1] != 90:
            warnings.warn(
                "Listed photometric type does not match last horizontal \
                angle value. Values will not be mirrored."
            )
        if phis[0] not in [-90, 0]:
            warnings.warn(
                "Listed photometric type does not match first horizontal \
                angle value. Values will not be mirrored."
            )
        for val in [-90, 0]:
            if phis[0] == val:
                lamp_type += str(val)
                extend_values = True
    else:
        warnings.warn(
            "Photometry type could not be determined. \
            Values will not be mirrored."
        )

    # list only currently supported lamp types
    if lamp_type not in ["C0", "C90", "C180", "C360"]:
        extend_values = False

    lampdict["lamp_type"] = lamp_type
    lampdict["extend_values"] = extend_values

    return lampdict


def _format_angles(lampdict):
    """
    Read the lamp symmetry and mirror the values accordingly

    TODO: add support for type A and B photometry
    https://support.agi32.com/support/solutions/articles/22000209748-type-a-type-b-and-type-c-photometry

    """

    newdict = {}
    lampdict["extended_vals"] = {}

    valdict = lampdict["original_vals"]
    lamp_type = lampdict["lamp_type"]

    newthetas = valdict["thetas"].copy()

    if lamp_type == "C0":
        # total radial symmetry
        # extend phis
        phis = valdict["phis"].copy()
        newphis = np.arange(0, 360)

        # extend values
        values = valdict["values"].copy().reshape(-1)
        newvals = np.tile(values, 360).reshape(-1, 360)

    elif lamp_type == "C90":
        # quaternary symmetry; each quadrant is identical
        # extend phis
        phis = valdict["phis"].copy()
        phis2 = phis[1:] + 90
        phis3 = phis[1:] + 180
        phis4 = phis[1:] + 270
        newphis = np.concatenate((phis, phis2, phis3, phis4))

        # extend values
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

    elif lamp_type == "C360":
        # no symmetry; extended values are identical to original values
        newphis = valdict["phis"].copy()
        newthetas = valdict["thetas"].copy()
        newvals = valdict["values"].copy()

    newdict["phis"] = newphis
    newdict["thetas"] = newthetas
    newdict["values"] = newvals

    lampdict["extended_vals"] = newdict

    return lampdict


def read_ies_data(path_to_file):
    lines = _read_file(path_to_file)
    lines = [line.strip() for line in lines]

    lampdict = {"source": path_to_file}
    lampdict["Version"] = _get_version(lines)

    header = []
    for i, line in enumerate(lines):
        header.append(line)
        if line.startswith("TILT="):
            if line == "TILT=NONE" or line == "TILT=<filename>":
                i = i + 1
            elif line == "TILT=INCLUDE":
                i = i + 5
            break
    lampdict["Header"] = _process_keywords(header, lampdict)

    # all remaining data should be numeric
    data = " ".join(lines[i:]).split()
    lampdict = _process_header(data, lampdict)

    lampdict = _read_angles(data, lampdict)
    lampdict = _get_lamp_type(lampdict)

    if lampdict["extend_values"]:
        lampdict = _format_angles(lampdict)

    return lampdict
