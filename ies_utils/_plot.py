import numpy as np
import matplotlib.pyplot as plt
from ._interpolate import get_intensity
from ._read import read_ies_data


def plot_ies(
    filename,
    which="interpolated",
    elev=-90,
    azim=90,
    title="",
    figsize=(6, 4),
    show_cbar=False,
    alpha=0.7,
    cmap="rainbow",
):
    """
    central plotting function
    
    TODO: make it possible to pass fig, ax arguments to this function
    """

    if which.lower() not in ["original","full", "interpolated"]:
        msg = "Argument `which` must be in [`original`, `full`, `interpolated`]"
        raise KeyError(msg)

    lampdict = read_ies_data(filename)

    if which.lower() == "original":
        thetas = lampdict["original_vals"]["thetas"]
        phis = lampdict["original_vals"]["phis"]
        values = lampdict["original_vals"]["values"]
        x, y, z = get_coords(thetas, phis, which="cartesian")
        intensity = values.flatten()

    elif which.lower() == "full":
        thetas = lampdict["full_vals"]["thetas"]
        phis = lampdict["full_vals"]["phis"]
        values = lampdict["full_vals"]["values"]
        x, y, z = get_coords(thetas, phis, which="cartesian")
        intensity = values.flatten()

    elif which.lower() == "interpolated":
        thetamap = lampdict["full_vals"]["thetas"]
        phimap = lampdict["full_vals"]["phis"]
        valuemap = lampdict["full_vals"]["values"].reshape(
            len(phimap), len(thetamap)
        )

        newthetas = np.linspace(0, 180, 100)
        newphis = np.linspace(0, 360, 100)

        thetaflat, phiflat = get_coords(newthetas, newphis, which="polar")
        intensity = [
            get_intensity(theta, phi, thetamap, phimap, valuemap)
            for theta, phi in zip(thetaflat, phiflat)
        ]
        x, y, z = get_coords(newthetas, newphis, which="cartesian")

    plot_3d(
        x,
        y,
        z,
        intensity,
        elev=elev,
        azim=azim,
        title=title,
        figsize=figsize,
        show_cbar=show_cbar,
        alpha=alpha,
        cmap=cmap,
    )


def plot_3d(
    x,
    y,
    z,
    intensity,
    elev=-90,
    azim=90,
    title="",
    figsize=(6, 4),
    show_cbar=False,
    alpha=0.7,
    cmap="rainbow",
):
    """
    Make a 3d intensity plot

    x,y,z: cartesian coordinates, must be 1-D arraylike
    intensity: value associated with coordinates,
    elev: configure alitude of camera angle of 3d plot (0-90 degrees). Defa
    azim: configure horizontal/azimuthal camera angle of 3d plot
    show_cbar: Optionally show colorbar of intensity values (default=False)
    figsize: alter figure size  (default=(6,4))
    alpha: transparency, 0-1 (default=0.7)
    cmap: colormap keyword (default='rainbow')
    """

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
    x = np.sin(theta_rad) * np.sin(phi_rad)
    y = np.sin(theta_rad) * np.cos(phi_rad)
    z = np.cos(theta_rad)

    return x, y, z


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
