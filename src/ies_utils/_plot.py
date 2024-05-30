import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import pathlib
import warnings
from ._interpolate import interpolate_values
from ._read import read_ies_data

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
    central plotting function
    
    Parameters::

    fdata: pathlike str, pathlib.PosixPath, dict
        either a filename or a lampdict object or a valdict object
    plot_type: str, default=`polar`
        if `polar`, standard ies file polar plot. if `cartesian`, a value-colored 3d plot of the measurements in cartesian space
    which: [`original`, `full`, `interpolated`], default=`interpolated
        only used if fdata is not a valdict object
    elev: numeric
        only used if plot_type=`cartesian`
    azim: numeric
        only used if plot_type=`cartesian`
    title: str
        title for plot
    figsize:
        actually probably not really used right now because both plot types are special
    show_cbar:
        if plot_type=`cartesian`, shows value intensity map
    cmap:
        colormap; used only if plot_type=`cartesian`

    """
    

    if which.lower() not in ["original", "full", "interpolated"]:
        msg = "`which` must be in [`original`, `full`, `interpolated`]"
        raise KeyError(msg)

    if plot_type.lower() not in ["polar", "cartesian"]:
        msg = "`plot_type` must be in [`polar`, `cartesian`]"
        raise KeyError(msg)

    # check what type filedata is
    DATA_TYPE = None
    if isinstance(fdata,(str,pathlib.PosixPath,bytes)):
        if Path(fdata).is_file():
            DATA_TYPE = "FILE"
            lampdict = read_ies_data(fdata)
    elif isinstance(fdata,dict):
        lampdict_keys = ['source', 'version', 'keywords', 'num_lamps', 'lumens_per_lamp', 'multiplier', 'num_vertical_angles', 'num_horizontal_angles', 'photometric_type', 'units_type', 'width', 'length', 'height', 'ballast_factor', 'future_use', 'input_watts', 'lamp_type', 'original_vals']
        valdict_keys = ['thetas','phis','values']
        if all([key in fdata.keys() for key in lampdict_keys]):
            DATA_TYPE = "LAMPDICT"
            lampdict = fdata
        elif all([key in fdata.keys() for key in valdict_keys]):
            DATA_TYPE = "VALDICT"
            valdict = fdata
        else:
            raise Exception("Datatype could not be determined")

    # load valdict if one was not passed 
    if DATA_TYPE != "VALDICT":
        if which.lower() == "original":
            valdict = lampdict["original_vals"]
        elif which.lower() == "full":
            valdict = lampdict["full_vals"]
        elif which.lower() == "interpolated":
            try:
                valdict = lampdict["interp_vals"]
            except KeyError:
                interpolate_values(lampdict)
                valdict = lampdict["interp_vals"]

    if plot_type == "polar":
        fig, ax = plot_valdict_polar(valdict=valdict, title=title, figsize=figsize)
        
    elif plot_type == "cartesian":
        fig, ax =  plot_valdict_cartesian(
                valdict=valdict,
                elev=elev,
                azim=azim,
                title=title,
                figsize=figsize,
                show_cbar=show_cbar,
                alpha=alpha,
                cmap=cmap,
            )
    return fig, ax

def plot_valdict_polar(valdict, title="", figsize=(6.4, 4.8)):
    values = valdict["values"]
    thetas = valdict["thetas"]
    phis = valdict["phis"]

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=figsize)

    # left and right 'sides' of the plot
    theta1 = np.radians(thetas)
    theta2 = np.radians((thetas + 180)[1:])

    # c0-c180
    try:
        r1 = values[phis == 0][0]
        ax.plot(theta1, r1, color="red", label="C0° - C180°")
    except IndexError:
        msg = "Phi values for 0 degrees not found"
        warnings.warn(msg, stacklevel=2)
    try:
        r2 = values[phis == 180][0]
        r2 = np.flip(r2)[1:]
        ax.plot(theta2, r2, color="red", label="C0° - C180°")
    except IndexError:
        msg = "Phi values for 180 degrees not found"
        warnings.warn(msg, stacklevel=2)

    # c90-c270
    try:
        r3 = values[phis == 90][0]
        ax.plot(theta1, r3, color="blue", label="C90° - C270°")
    except IndexError:
        msg = "Phi values for 90 degrees not found"
        warnings.warn(msg, stacklevel=2)
    try:
        r4 = values[phis == 270][0]
        r4 = np.flip(r4)[1:]
        ax.plot(theta2, r4, color="blue", label="C90° - C270°")
    except IndexError:
        msg = "Phi values for 90 degrees not found"
        warnings.warn(msg, stacklevel=2)

    # max candela
    max_candela_phi = phis[np.argmax(np.max(values, axis=1))]
    if max_candela_phi not in [0, 90, 180, 270]:
        r5 = values[phis == max_candela_phi][0]
        label = "Max Candela: " + str(max_candela_phi) + "°"
        ax.plot(theta1, r5, color="purple", label=label)

    # plot formatting
    ax.set_theta_zero_location("S")
    ax.set_rlabel_position(0)  # Move radial labels away from plotted line
    plt.setp(ax.get_yticklabels(), alpha=0.5, rotation=45, fontsize=9)
    ax.grid(True)
    ax.set_title(title)

    # relabel tick marks
    labs = ax.get_xticklabels()[0:5]
    morelabs = labs.copy()
    morelabs.reverse()
    newlabs = labs[:-1] + morelabs[:-1]
    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels(newlabs)

    # legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), 
            loc='upper center',
            bbox_to_anchor=[0.5,-0.1,0,0 ],
    )
    plt.tight_layout()
    plt.show()
    
    return fig, ax


def plot_valdict_cartesian(
    valdict,
    elev=-90,
    azim=90,
    title="",
    figsize=(6, 4),
    show_cbar=False,
    alpha=0.7,
    cmap="rainbow",
):
    """
    valdict: dictionary containing thetas, phis, and the candela values
    elev: configure alitude of camera angle of 3d plot (0-90 degrees).
    azim: configure horizontal/azimuthal camera angle of 3d plot
    show_cbar: Optionally show colorbar of intensity values (default=False)
    figsize: alter figure size  (default=(6,4))
    alpha: transparency, 0-1 (default=0.7)
    cmap: colormap keyword (default='rainbow')

    TODO: make it possible to pass fig, ax arguments to this function
    """

    # verify valdict
    keys = list(valdict.keys())
    if not all(x in keys for x in ["thetas", "phis", "values"]):
        raise KeyError

    thetas = valdict["thetas"]
    phis = valdict["phis"]
    values = valdict["values"]

    # verify data shape
    if not values.shape == (len(phis), len(thetas)):
        msg = "Shape of candela values {} does not match number of vertical and \
            horizontal angles {}".format(
            values.shape, (len(phis), len(thetas))
        )
        raise ValueError(msg)

    x, y, z = get_coords(thetas, phis, which="cartesian")
    intensity = values.flatten()

    # plot
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    img = ax.scatter(x, y, z, c=intensity, cmap="rainbow", alpha=alpha)

    if show_cbar:
        cbar = fig.colorbar(img)
        cbar.set_label("Intensity")

    ax.view_init(azim=azim, elev=elev)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_title(title)
    plt.show()

    return fig, ax


def get_coords(thetas, phis, which="cartesian"):
    """
    Get an ordered pair of lists of coordinates.
    thetas: arraylike of vertical angles
    phis: arraylike of horizontal angles
    which: {'cartesian','polar'}
    """

    if which.lower() not in ["cartesian", "polar"]:
        raise Exception(
            "Invalid coordinate type: must be either `polar` or `cartesian`"
        )

    tgrid, pgrid = np.meshgrid(thetas, phis)
    tflat, pflat = tgrid.flatten(), pgrid.flatten()

    if which.lower() == "cartesian":
        coordslist = [polar_to_cartesian(t, p) for t, p in zip(tflat, pflat)]
        coords = np.array(coordslist).T
    elif which.lower() == "polar":
        coords = np.array([tflat, pflat])

    return coords


def polar_to_cartesian(theta, phi, distance=1):
    """
    Convert polar coordinates to cartesian coordinates.

    Parameters:
    theta (float): Polar angle in degrees. 0 degrees is down, 180 is up.
    phi (float): Azimuthal angle in degrees.
    distance (float): Radius value. Assumed to be 1 meter.

    Returns:
    tuple: (x, y, z, value) in Cartesian coordinates.
    """
    # Convert angles to radians
    theta_rad = np.radians(180 - theta)  # to account for reversed z direction
    phi_rad = np.radians(phi)

    # Polar to Cartesian conversion
    x = distance * np.sin(theta_rad) * np.sin(phi_rad)
    y = distance * np.sin(theta_rad) * np.cos(phi_rad)
    z = distance * np.cos(theta_rad)

    return x, y, z
